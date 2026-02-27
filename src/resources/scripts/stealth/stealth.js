// ========== 硬件参数伪造 ==========
Object.defineProperty(navigator, "hardwareConcurrency", {
  get: () => __HARDWARE_CONCURRENCY__,
});
Object.defineProperty(navigator, "deviceMemory", {
  get: () => __DEVICE_MEMORY__,
});

// ========== Screen 屏幕指纹伪造 ==========
Object.defineProperty(screen, "width", {
  get: () => __SCREEN_WIDTH__,
});
Object.defineProperty(screen, "height", {
  get: () => __SCREEN_HEIGHT__,
});
Object.defineProperty(screen, "availWidth", {
  get: () => __SCREEN_AVAIL_WIDTH__,
});
Object.defineProperty(screen, "availHeight", {
  get: () => __SCREEN_AVAIL_HEIGHT__,
});
Object.defineProperty(screen, "colorDepth", {
  get: () => __SCREEN_COLOR_DEPTH__,
});
Object.defineProperty(screen, "pixelDepth", {
  get: () => __SCREEN_PIXEL_DEPTH__,
});

// ========== WebGL 厂商与渲染器伪造 ==========
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (parameter) {
  // 37445: UNMASKED_VENDOR_WEBGL
  // 37446: UNMASKED_RENDERER_WEBGL
  if (parameter === 37445) {
    return "__WEBGL_VENDOR__";
  }
  if (parameter === 37446) {
    return "__WEBGL_RENDERER__";
  }
  return getParameter.apply(this, arguments);
};

// 针对 WebGL2 也做同样的修补
if (typeof WebGL2RenderingContext !== "undefined") {
  const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
  WebGL2RenderingContext.prototype.getParameter = function (parameter) {
    if (parameter === 37445) {
      return "__WEBGL_VENDOR__";
    }
    if (parameter === 37446) {
      return "__WEBGL_RENDERER__";
    }
    return getParameter2.apply(this, arguments);
  };
}

// ========== Navigator 扩展属性伪造 ==========
Object.defineProperty(navigator, "platform", {
  get: () => "__PLATFORM__",
});
Object.defineProperty(navigator, "maxTouchPoints", {
  get: () => __MAX_TOUCH_POINTS__,
});
Object.defineProperty(navigator, "vendor", {
  get: () => "__VENDOR__",
});
Object.defineProperty(navigator, "vendorSub", {
  get: () => "__VENDOR_SUB__",
});
Object.defineProperty(navigator, "productSub", {
  get: () => "__PRODUCT_SUB__",
});

// ========== 隐藏 webdriver 属性 ==========
Object.defineProperty(navigator, "webdriver", {
  get: () => undefined,
});

// ========== 伪造插件列表 ==========
Object.defineProperty(navigator, "plugins", {
  get: () => [
    { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer" },
    { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai" },
    { name: "Native Client", filename: "internal-nacl-plugin" },
  ],
});

// ========== 伪造 languages ==========
Object.defineProperty(navigator, "languages", {
  get: () => ["zh-CN", "zh", "en"],
});

// ========== 伪造 chrome 对象 ==========
if (!window.chrome) {
  window.chrome = {
    runtime: {},
    loadTimes: function () {},
    csi: function () {},
    app: {},
  };
}

// ========== 伪造 permissions 查询 ==========
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
  parameters.name === "notifications"
    ? Promise.resolve({ state: "granted" })
    : originalQuery(parameters);

// ========== Battery API 伪造 ==========
if (navigator.getBattery) {
  navigator.getBattery = () =>
    Promise.resolve({
      charging: __BATTERY_CHARGING__,
      chargingTime: 0,
      dischargingTime: Infinity,
      level: __BATTERY_LEVEL__,
      addEventListener: function () {},
      removeEventListener: function () {},
      dispatchEvent: function () {},
    });
}

// ========== Connection 网络连接伪造 ==========
if (navigator.connection) {
  Object.defineProperty(navigator.connection, "effectiveType", {
    get: () => "__CONNECTION_TYPE__",
  });
  Object.defineProperty(navigator.connection, "downlink", {
    get: () => __CONNECTION_DOWNLINK__,
  });
  Object.defineProperty(navigator.connection, "rtt", {
    get: () => __CONNECTION_RTT__,
  });
}

// ========== AudioContext 音频指纹噪声 ==========
const audioContextSeed = __AUDIO_CONTEXT_SEED__;
if (typeof AudioContext !== "undefined") {
  const OriginalAudioContext = AudioContext;
  window.AudioContext = function () {
    const context = new OriginalAudioContext(...arguments);
    const originalCreateOscillator = context.createOscillator.bind(context);
    context.createOscillator = function () {
      const oscillator = originalCreateOscillator();
      const originalStart = oscillator.start.bind(oscillator);
      oscillator.start = function (when) {
        // 添加基于种子的微小频率偏移
        oscillator.frequency.value += (audioContextSeed % 10) * 0.001;
        return originalStart(when);
      };
      return oscillator;
    };
    return context;
  };
}

// ========== Canvas 指纹噪声 (基于账号种子) ==========
const canvasNoiseSeed = __CANVAS_NOISE_SEED__;
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function (type) {
  if (type === "image/png" || type === "image/webp") {
    const canvas = this;
    const context = canvas.getContext("2d");
    if (context) {
      const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < imageData.data.length; i += 4) {
        // 基于种子的确定性噪声
        imageData.data[i] ^= canvasNoiseSeed % 3;
      }
      context.putImageData(imageData, 0, 0);
    }
  }
  return originalToDataURL.apply(this, arguments);
};

// ========== Font 字体指纹防护 ==========
// 返回固定的常见字体列表,避免暴露系统特有字体
const commonFonts = [
  "Arial",
  "Verdana",
  "Helvetica",
  "Times New Roman",
  "Courier New",
  "Georgia",
  "Palatino",
  "Garamond",
  "Bookman",
  "Comic Sans MS",
  "Trebuchet MS",
  "Impact",
  "Microsoft YaHei",
  "SimSun",
  "SimHei",
];

// 拦截字体检测
const originalOffsetWidth = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "offsetWidth",
);
const originalOffsetHeight = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "offsetHeight",
);

// ========== Timezone 一致性保护 ==========
// 确保 Date.getTimezoneOffset() 与设置的 timezone_id 一致
// Asia/Shanghai 的偏移量是 -480 (UTC+8)
const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
Date.prototype.getTimezoneOffset = function () {
  return -480; // UTC+8
};

// ========== WebRTC IP 泄露完全防护 ==========
// 方案1: 完全禁用 RTCPeerConnection
if (typeof RTCPeerConnection !== "undefined") {
  const OriginalRTCPeerConnection = RTCPeerConnection;
  window.RTCPeerConnection = function () {
    const pc = new OriginalRTCPeerConnection(...arguments);

    // 拦截 createOffer,过滤真实IP
    const originalCreateOffer = pc.createOffer.bind(pc);
    pc.createOffer = function () {
      return originalCreateOffer(...arguments).then((offer) => {
        // 替换SDP中的真实IP为0.0.0.0
        if (offer.sdp) {
          offer.sdp = offer.sdp.replace(
            /c=IN IP4 \d+\.\d+\.\d+\.\d+/g,
            "c=IN IP4 0.0.0.0",
          );
          offer.sdp = offer.sdp.replace(/a=candidate:.+?(\r\n|\n|$)/g, "");
        }
        return offer;
      });
    };

    return pc;
  };

  // 同步处理 webkit 前缀
  if (typeof webkitRTCPeerConnection !== "undefined") {
    window.webkitRTCPeerConnection = window.RTCPeerConnection;
  }
}

// ========== Media Devices 伪造 ==========
if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
  const fakeDevices = [
    {
      deviceId: "default",
      kind: "audioinput",
      label: "Default - Microphone (Realtek High Definition Audio)",
      groupId: "group-audio-input-1",
    },
    {
      deviceId: "communications",
      kind: "audioinput",
      label: "Communications - Microphone (Realtek High Definition Audio)",
      groupId: "group-audio-input-1",
    },
    {
      deviceId: "default",
      kind: "audiooutput",
      label: "Default - Speakers (Realtek High Definition Audio)",
      groupId: "group-audio-output-1",
    },
    {
      deviceId: "webcam-1",
      kind: "videoinput",
      label: "HD Webcam (04f2:b5ce)",
      groupId: "group-video-input-1",
    },
  ];

  navigator.mediaDevices.enumerateDevices = () => Promise.resolve(fakeDevices);
}

// ========== Permissions API 完善 ==========
if (navigator.permissions && navigator.permissions.query) {
  const originalPermissionsQuery = navigator.permissions.query;
  const permissionsMap = {
    notifications: "granted",
    geolocation: "prompt",
    camera: "prompt",
    microphone: "prompt",
    "clipboard-read": "denied",
    "clipboard-write": "granted",
    "persistent-storage": "granted",
    push: "prompt",
    midi: "prompt",
  };

  navigator.permissions.query = function (params) {
    const permName =
      params.name || (params.descriptor && params.descriptor.name);
    if (permName && permissionsMap[permName]) {
      return Promise.resolve({ state: permissionsMap[permName] });
    }
    return originalPermissionsQuery.apply(this, arguments);
  };
}

// ========== Intl 国际化一致性 ==========
// 确保时区、语言等国际化设置一致
if (typeof Intl !== "undefined" && Intl.DateTimeFormat) {
  const OriginalDateTimeFormat = Intl.DateTimeFormat;
  Intl.DateTimeFormat = function (locales, options) {
    // 强制使用中文和上海时区
    const newLocales = locales || "zh-CN";
    const newOptions = options || {};
    if (!newOptions.timeZone) {
      newOptions.timeZone = "Asia/Shanghai";
    }
    return new OriginalDateTimeFormat(newLocales, newOptions);
  };

  // 保留原型链
  Intl.DateTimeFormat.prototype = OriginalDateTimeFormat.prototype;
  Intl.DateTimeFormat.supportedLocalesOf =
    OriginalDateTimeFormat.supportedLocalesOf;
}

// ========== CDP/Playwright/Puppeteer 检测绕过 ==========
// 删除自动化工具留下的痕迹
delete window.__playwright;
delete window.__puppeteer;
delete window.__selenium;
delete window.callPhantom;
delete window._phantom;
delete window.__nightmare;
delete window.__fxdriver_unwrapped;
delete window.__webdriver_unwrapped;
delete window.__driver_evaluate;
delete window.__webdriver_evaluate;
delete window.__selenium_evaluate;
delete window.__fxdriver_evaluate;
delete window.__driver_unwrapped;
delete window.__webdriver_script_function;
delete window.__webdriver_script_func;
delete window.__webdriver_script_fn;

// ========== Headless 检测绕过 ==========
// 伪造 window.outerWidth/outerHeight (headless模式下这些值为0)
if (window.outerWidth === 0) {
  Object.defineProperty(window, "outerWidth", {
    get: () => window.innerWidth,
  });
}
if (window.outerHeight === 0) {
  Object.defineProperty(window, "outerHeight", {
    get: () => window.innerHeight + 85, // 加上浏览器UI高度
  });
}

// 伪造 chrome.runtime (headless模式下可能缺失)
if (window.chrome && !window.chrome.runtime) {
  window.chrome.runtime = {
    connect: function () {},
    sendMessage: function () {},
    onMessage: {
      addListener: function () {},
      removeListener: function () {},
    },
  };
}

// ========== 其他高级伪造 ==========
// 伪造 window.external (IE遗留,但某些检测会查看)
if (!window.external) {
  window.external = {
    AddSearchProvider: function () {},
    IsSearchProviderInstalled: function () {},
  };
}

// 伪造 navigator.mimeTypes
Object.defineProperty(navigator, "mimeTypes", {
  get: () => [
    {
      type: "application/pdf",
      suffixes: "pdf",
      description: "Portable Document Format",
    },
    {
      type: "application/x-google-chrome-pdf",
      suffixes: "pdf",
      description: "Portable Document Format",
    },
  ],
});

// 确保 navigator.doNotTrack 存在
if (typeof navigator.doNotTrack === "undefined") {
  Object.defineProperty(navigator, "doNotTrack", {
    get: () => null,
  });
}
