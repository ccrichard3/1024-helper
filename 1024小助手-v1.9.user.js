// ==UserScript==
// @name         1024小助手
// @namespace    https://greasyfork.org/zh-CN/scripts/489614-1024%E5%B0%8F%E5%8A%A9%E6%89%8B
// @version      1.9
// @description  草榴社区帖子页自动点赞、限版块自动随机回复、自动回复开关、内置回复库管理、主题图片视频下载、无图模式、返回顶部、防去广告检测
// @author       ccrichard3
// @match        *://*/htm_data/*
// @match        *://*/thread*
// @match        *://*/@*
// @match        http*://*/htm_data/*.html
// @match        http*://*/htm_mob/*.html
// @match        http*://*/read.php?*
// @match        http*://*/search.php?*
// @match        http*://*/personal.php*
// @match        http*://*/post.php*
// @match        http*://*/thread0806.php*
// @require      https://code.jquery.com/jquery-1.12.4.min.js
// @grant        GM_download
// @run-at       document-body
// @license      MIT License
// @downloadURL  https://update.greasyfork.org/scripts/489614/1024%E5%B0%8F%E5%8A%A9%E6%89%8B.user.js
// @updateURL    https://update.greasyfork.org/scripts/489614/1024%E5%B0%8F%E5%8A%A9%E6%89%8B.meta.js
// ==/UserScript==

(function () {
  'use strict';

  /* ------------------- 防广告检测 ------------------- */
  $('<div>').addClass('tpc_content').insertBefore("body").html("TEST").css({
    'position': 'absolute',
    'top': '-9950px',
    'left': '-9990px'
  });

  const cssStr = `
    #ImageView{position:fixed;top:0;right:0;z-index:9999;background:#000;padding:10px;height:100vh;overflow:auto}
    #ImageView img{width:100%;margin-bottom:20px}
    #ImageView #close{position:fixed;top:10px;right:26px;z-index:10000;padding:10px;cursor:pointer;background:rgba(255,255,255,.5)}
    .newPost{color:#2563eb!important}.newPost a,.newPost .tal a{color:#2563eb!important}
    h3 a:visited{color:#999!important}
    .img-box{margin-left:-10px}
    .image-container{position:relative;float:left;width:200px;height:200px;margin-bottom:10px;margin-left:10px;overflow:hidden;display:flex;justify-content:center;align-items:center;border:1px solid #ccc}
    .image-container img{max-width:100%;max-height:100%;object-fit:contain}
    .image-container b{position:absolute;top:0;left:0;color:#000!important}
    .image-container span{display:none;position:absolute;top:0;right:0;font-size:12px;color:#000!important;cursor:pointer}
    .image-container:hover span{display:block}
    .back-to-top{position:fixed;bottom:20px;right:20px;width:50px;height:50px;background-color:#3498db;border-radius:50%;cursor:pointer;z-index:9999;text-align:center;transition:all .3s ease}
    .back-to-top::before{content:"↑";color:#fff;font-size:24px;line-height:50px;text-align:center}
    .reply-helper{--helper-peek:46px;position:fixed;right:20px;bottom:84px;z-index:9999;width:max-content;max-width:min(272px,calc(100vw - 24px));background:rgba(255,255,255,.94);border:1px solid #d9e6ff;border-radius:14px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.12);font-size:12px;line-height:1.45;backdrop-filter:blur(6px);transition:opacity .18s ease,transform .18s ease,padding .18s ease,right .18s ease}
    .reply-helper.is-docked-right{left:auto!important;right:12px}
    .reply-helper.is-collapsed{opacity:.68;padding:7px 10px;transform:translateX(calc(100% - var(--helper-peek)));max-width:176px}
    .reply-helper-title{font-weight:bold;margin-bottom:4px;color:#345;cursor:move;user-select:none}
    .reply-helper-meta{margin-bottom:6px;color:#678;font-size:11px}
    .reply-helper-draft{margin-bottom:8px;color:#222;white-space:pre-wrap;word-break:break-word;font-size:12px}
    .reply-helper-actions{display:flex;gap:6px;flex-wrap:nowrap}
    .reply-helper-btn{padding:3px 10px;border:1px solid #7aa7ff;border-radius:999px;background:#eef4ff;color:#2457c5;cursor:pointer;font-size:12px}
    .reply-helper-btn:hover{background:#dfeaff}
    .reply-helper-row{display:flex;gap:6px;flex-wrap:nowrap;margin-bottom:6px}
    .reply-helper-row:last-of-type{margin-bottom:0}
    .reply-helper.is-collapsed .reply-helper-meta,.reply-helper.is-collapsed .reply-helper-draft,.reply-helper.is-collapsed .reply-helper-row,.reply-helper.is-collapsed .reply-helper-list{display:none!important}
    .reply-helper.is-collapsed .reply-helper-title{margin-bottom:0}
    .reply-helper-list{display:none;margin-top:8px;max-height:220px;overflow:auto;border-top:1px solid #e4ecff;padding-top:8px}
    .reply-helper-list.is-open{display:block}
    .reply-helper-list-tools{display:flex;align-items:center;gap:6px;margin-bottom:6px}
    .reply-helper-list-input{flex:1;min-width:0;padding:4px 8px;border:1px solid #bfd2ff;border-radius:9px;background:#fff;color:#234;font-size:12px}
    .reply-helper-list-row{display:flex;align-items:flex-start;gap:6px;margin-bottom:6px}
    .reply-helper-list-text{flex:1;white-space:pre-wrap;word-break:break-word;color:#234;padding:2px 4px;border-radius:8px}
    .reply-helper-list-text.is-editing{outline:1px solid #7aa7ff;background:#f3f7ff}
    .reply-helper-list-del{padding:1px 7px;border-radius:999px;cursor:pointer;font-size:11px}
    .reply-helper-list-del{padding:1px 7px;border:1px solid #ffb3b3;border-radius:999px;background:#fff2f2;color:#cc4b4b;cursor:pointer;font-size:11px}
    .reply-helper-list-empty{color:#789;font-size:11px}
    .reply-helper-btn.is-active{background:#dbe8ff}
    .cl-no-image img,.cl-no-image video{display:none!important}
    .cl-no-image .banner{display:none!important}
  `;

  const helper = {
    addCss: function (css) {
      var style = document.createElement('style');
      style.type = 'text/css';
      style.appendChild(document.createTextNode(css));
      document.head.appendChild(style);
    },
    timeFormat: function (data, format) {
      var o = {
        'M+': data.getMonth() + 1,
        'd+': data.getDate(),
        'h+': data.getHours(),
        'm+': data.getMinutes(),
        's+': data.getSeconds()
      };
      if (/(y+)/.test(format)) {
        format = format.replace(RegExp.$1, (data.getFullYear() + '').substr(4 - RegExp.$1.length));
      }
      for (var k in o)
        if (new RegExp('(' + k + ')').test(format))
          format = format.replace(RegExp.$1, RegExp.$1.length === 1 ? o[k] : ('00' + o[k]).substr(('' + o[k]).length));
      return format;
    },
    inurl: function (str) {
      return document.location.href.indexOf(str) >= 0;
    },
    scrollToElement: function (id) {
      var el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    },
    replaceStr: function (str = "") {
      return str?.replace(/\.jpg\.[^/]+\//g, '.jpg.dog/')
        .replace(".ca11tbox.moe", ".catbox.moe")
        .replace(".c111atbox.moe", ".catbox.moe")
        .replace("catbox.m22o1e/", "catbox.moe/")
        .replace(/\66img\.[^/]+\//g, '66img.cc/')
        .replace("66im6g.", "66img.")
        .replace("666img.", "66img.")
        .replace("663img.", "66img.");
    }
  };

  helper.addCss(cssStr);

  function reloadImageUrls() {
    document.querySelectorAll('#conttpc img').forEach((img, index) => {
      img.src = helper.replaceStr(img.src);
      img.onclick = function () {
        openImgAlert();
        setTimeout(() => helper.scrollToElement('img_' + index), 500);
      };
    });
    document.querySelectorAll('#conttpc video').forEach(video => {
      video.src = helper.replaceStr(video.src);
    });
  }

  function batchDownloadImages() {
    document.querySelectorAll('#conttpc img, #conttpc video').forEach((item, index) => {
      const url = item?.src || '';
      const name = `[${index + 1}]${url.substring(url.lastIndexOf('/') + 1)}`;
      GM_download(url, name);
    });
  }

  function openImgAlert() {
    const imgs = [...document.querySelectorAll('#conttpc img')].map((i, idx) => `<img id="img_${idx}" src="${i.src}"/>`);
    if (!$('#ImageView').length) {
      $('body').append(`
        <div id="ImageView">
          <div id="close">关闭</div>
          ${imgs.join('')}
        </div>
      `);
      $('#ImageView #close').on('click', function () {
        $('#ImageView').remove();
      });
    }
  }

  function addBackToTop() {
    if (document.querySelector('.back-to-top')) {
      return;
    }
    const btn = document.createElement('div');
    btn.className = 'back-to-top';
    btn.title = '返回顶部';
    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    document.body.appendChild(btn);
  }

  function findPromptRedirectLink() {
    const links = [...document.querySelectorAll('a[href]')];
    return links.find((link) => {
      const text = (link.textContent || '').replace(/\s+/g, '');
      const href = link.href || '';
      return /如果您的瀏覽器沒有自動跳轉|如果您的浏览器没有自动跳转|點擊這裡|点击这里/.test(text)
        && /(read\.php|htm_data|thread|post\.php)/i.test(href);
    }) || null;
  }

  function findReturnContinueButton() {
    return [...document.querySelectorAll('input[type="button"], button, a[href], input[type="submit"]')]
      .find((node) => /返\s*回\s*繼\s*續\s*操\s*作|返回继续操作|返回繼續操作/.test(node.value || node.textContent || '')) || null;
  }

  function goBackToContinue(backBtn) {
    if (backBtn) {
      backBtn.click();
      return;
    }
    if (document.referrer) {
      window.location.replace(document.referrer);
      return;
    }
    if (history.length > 1) {
      history.back();
    }
  }

  function handlePromptPages() {
    const bodyText = (document.body?.innerText || '').replace(/\s+/g, ' ').trim();

    const redirectLink = findPromptRedirectLink();
    if (redirectLink && redirectLink.href && redirectLink.href !== window.location.href) {
      setTimeout(() => {
        window.location.replace(redirectLink.href);
      }, 80);
      return true;
    }

    const backBtn = findReturnContinueButton();
    const isForumPromptPage = /論壇提示|论坛提示|提示信息/.test(bodyText)
      || /論壇提示|论坛提示|提示信息/.test(document.title || '');
    if (backBtn && isForumPromptPage) {
      setTimeout(() => goBackToContinue(backBtn), 80);
      return true;
    }

    const isFloodGuardPage = /灌水預防機制已經打開|灌水预防机制已经打开/.test(bodyText)
      && /1024秒內不能發貼|1024秒内不能发贴/.test(bodyText);

    if (isFloodGuardPage) {
      setTimeout(() => goBackToContinue(backBtn), 80);
      return true;
    }

    return false;
  }

  function getThreadTitle() {
    const titleNode = document.querySelector('h1') || document.querySelector('title');
    const rawTitle = (titleNode?.textContent || '').trim();
    if (!rawTitle) {
      return '这个帖子';
    }
    return rawTitle
      .replace(/\s*-\s*.*$/, '')
      .replace(/\s*Powered by.*$/i, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function getReplyTextarea() {
    const areas = [
      ...document.querySelectorAll('textarea[name], textarea[id], form textarea, textarea')
    ];
    return areas.find((area) => {
      const style = window.getComputedStyle(area);
      return !area.disabled && style.display !== 'none' && style.visibility !== 'hidden';
    }) || null;
  }

  function getCurrentForumId() {
    const inputFid = document.querySelector('input[name="fid"]')?.value;
    if (inputFid && /^\d+$/.test(inputFid)) {
      return Number(inputFid);
    }

    const url = new URL(window.location.href);
    const fid = url.searchParams.get('fid');
    if (fid && /^\d+$/.test(fid)) {
      return Number(fid);
    }

    const scriptMatch = document.body.innerHTML.match(/\bfid\s*=\s*(\d+)/i);
    if (scriptMatch) {
      return Number(scriptMatch[1]);
    }

    return null;
  }

  function isAutoReplyAllowedForum() {
    const fid = getCurrentForumId();
    return fid != null && AUTO_REPLY_ALLOWED_FORUM_IDS.has(fid);
  }

  function randomBetween(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function escapeHtml(text = '') {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  const REPLY_ANALYTICS_KEY = 'cl1024-reply-analytics-v1';
  const REPLY_FORUM_IDS = [2, 15, 4, 5, 25, 26, 28];
  const AUTO_REPLY_ALLOWED_FORUM_IDS = new Set(REPLY_FORUM_IDS);
  const AUTO_REPLY_DELAY_MIN = 1800;
  const AUTO_REPLY_DELAY_MAX = 6200;
  const PROCESSED_THREAD_TTL = 12 * 60 * 60 * 1000;
  const DEFAULT_REPLY_LIBRARY = [
    '这个帖子挺实用 收下了',
    '楼主发帖辛苦 支持一下',
    '支持优质内容 感谢更新',
    '帖子看着很顺 感谢分享',
    '整理得很省事 支持',
    '质量在线 先回再看',
    '这帖不错 收藏慢慢看',
    '分享很及时 支持一下',
    '内容挺全 感谢整理分享',
    '资源质量不错 感谢楼主',
    '这次更新很稳 支持一下',
    '内容看着很顺 先收下',
    '楼主整理得很清楚',
    '质量不错 感谢持续更新',
    '这帖有点东西 先留着',
    '看起来挺有料 感谢分享',
    '楼主辛苦了 内容不错',
    '资源挺整齐 看着舒服',
    '这波分享可以 感谢楼主',
    '内容很实在 支持一下',
    '这帖质量在线 收下了',
    '分享很到位 感谢整理',
    '楼主这次发得不错',
    '内容挺全 省得再找了',
    '这帖很稳 先赞再看',
    '感谢补档 看着不错',
    '资源不错 先收藏起来',
    '楼主用心了 支持一波',
    '帖子质量可以 感谢更新',
    '这个分享挺及时 收下',
    '楼主辛苦 这帖不错',
    '整理得很顺眼 感谢',
    '内容不错 留着慢慢看',
    '这次分享质量挺高',
    '感谢楼主带来好内容',
    '帖子不错 支持一下',
    '内容挺有看点 感谢',
    '这帖看起来很稳',
    '质量挺好 先收一份',
    '楼主更新及时 感谢',
    '资源很实在 支持楼主',
    '看着不错 感谢整理',
    '这波内容可以 先留着',
    '分享挺靠谱 感谢',
    '内容不错 支持发帖',
    '这帖有收藏价值',
    '资源看着很舒服 感谢',
    '更新很及时 支持一下',
    '楼主这帖质量可以',
    '这份内容挺完整',
    '看完再来支持一下',
    '整理不容易 感谢楼主',
    '这次内容很到位',
    '好帖先收着 感谢',
    '内容很顺 支持分享',
    '这帖值得留一手',
    '分享不错 多谢整理',
    '看着质量很稳 感谢',
    '帖子挺有诚意 支持',
    '楼主继续保持这个质量'
  ];
  const REMOVED_REPLY_LIBRARY = new Set([
    '1024 nb 再接再厉',
    'bb皮肤好',
    'nice👍',
    '好奶好B好屁',
    'thanks',
    '都是D以上的吧',
    '奶头1.5cm',
    '感谢分享 干净B',
    '我喜欢cream',
    '等待新IP 谢谢',
    '好看的b 感谢分享',
    '真够大的 好看得有e了吧',
    '感谢分享 内容不错',
    '楼主辛苦了 这帖有用',
    '支持一下 先收藏再看',
    '这个整理挺完整 感谢',
    '看起来不错 感谢楼主',
    '内容很实在 支持分享',
    '这帖质量可以 先留个爪',
    '感谢整理 信息很清楚',
    '先赞后看 感谢分享',
    '资源和说明都很到位 感谢',
    '看完感觉很值 感谢整理',
    '内容不错 收藏备用',
    '这次分享挺稳 感谢楼主',
    '看标题就有兴趣 感谢',
    '感谢楼主带来好内容'
  ]);

  function createReplyAnalytics() {
    return {
      version: 1,
      threadCount: 0,
      replyCount: 0,
      processedThreads: {},
      freq: {},
      customReplies: [],
      hiddenReplies: [],
      list: [...DEFAULT_REPLY_LIBRARY],
      updatedAt: Date.now()
    };
  }

  function loadReplyAnalytics() {
    try {
      const data = JSON.parse(localStorage.getItem(REPLY_ANALYTICS_KEY) || 'null');
      if (!data || typeof data !== 'object') {
        return createReplyAnalytics();
      }
      const now = Date.now();
      const processedThreads = Object.fromEntries(
        Object.entries(data.processedThreads || {}).filter(([, ts]) => {
          const time = Number(ts) || 0;
          return time > 0 && now - time < PROCESSED_THREAD_TTL;
        })
      );
      const freq = {};
      Object.entries(data.freq || {}).forEach(([rawText, count]) => {
        const text = normalizeReplyCandidate(rawText);
        if (!text || REMOVED_REPLY_LIBRARY.has(text)) {
          return;
        }
        freq[text] = (freq[text] || 0) + (Number(count) || 0);
      });
      const hiddenReplies = [...new Set(
        (Array.isArray(data.hiddenReplies) ? data.hiddenReplies : [])
          .map((text) => normalizeReplyCandidate(text))
          .filter((text) => text && !REMOVED_REPLY_LIBRARY.has(text))
      )];
      const hiddenSet = new Set(hiddenReplies);
      const customReplies = [...new Set(
        (Array.isArray(data.customReplies) ? data.customReplies : [])
          .map((text) => normalizeReplyCandidate(text))
          .filter((text) => text && !REMOVED_REPLY_LIBRARY.has(text) && !hiddenSet.has(text))
      )];
      const legacyListReplies = [...new Set(
        (Array.isArray(data.list) ? data.list : [])
          .map((text) => normalizeReplyCandidate(text))
          .filter((text) => text && !REMOVED_REPLY_LIBRARY.has(text) && !hiddenSet.has(text))
      )];
      const mergedCustomReplies = [...new Set([
        ...customReplies,
        ...legacyListReplies.filter((text) => !DEFAULT_REPLY_LIBRARY.includes(text))
      ])];
      const list = buildReplyLibrary(freq, hiddenReplies, mergedCustomReplies);
      return {
        ...createReplyAnalytics(),
        ...data,
        threadCount: Object.keys(processedThreads).length,
        processedThreads,
        freq,
        customReplies: mergedCustomReplies,
        hiddenReplies,
        list: list.length ? list : [...DEFAULT_REPLY_LIBRARY]
      };
    } catch (error) {
      return createReplyAnalytics();
    }
  }

  function saveReplyAnalytics(data) {
    localStorage.setItem(REPLY_ANALYTICS_KEY, JSON.stringify(data));
  }

  function normalizeReplyCandidate(text = '') {
    return text
      .replace(/\u3000/g, ' ')
      .replace(/^Re[:：]?\s*/i, '')
      .replace(/[，,]+/g, ' ')
      .replace(/[。.]+/g, '')
      .replace(/\s+/g, ' ')
      .replace(/[“”"'`]/g, '')
      .replace(/[!！~～、;；:：]+$/g, '')
      .trim();
  }

  function isUsefulReplyCandidate(text = '') {
    if (!text || text.length < 4 || text.length > 36) {
      return false;
    }
    if (REMOVED_REPLY_LIBRARY.has(text)) {
      return false;
    }
    if (/https?:\/\//i.test(text) || /www\./i.test(text)) {
      return false;
    }
    if (/(微信|vx|v信|qq|电报|tg|群号|群聊)/i.test(text)) {
      return false;
    }
    if ((text.match(/\d/g) || []).length >= 6) {
      return false;
    }
    if (/^[\d\W_]+$/.test(text)) {
      return false;
    }
    if (/^(沙发|板凳|顶帖|路过|马克|mark|1024)$/i.test(text)) {
      return false;
    }
    return true;
  }

  function buildReplyLibrary(freq = {}, hiddenReplies = [], customReplies = []) {
    const hiddenSet = new Set(hiddenReplies);
    const ranked = Object.entries(freq)
      .filter(([text]) => isUsefulReplyCandidate(text) && !hiddenSet.has(text))
      .sort((a, b) => b[1] - a[1] || a[0].length - b[0].length)
      .map(([text]) => text);

    const manual = customReplies
      .map((text) => normalizeReplyCandidate(text))
      .filter((text) => isUsefulReplyCandidate(text) && !hiddenSet.has(text));

    return [...new Set([
      ...manual,
      ...ranked,
      ...DEFAULT_REPLY_LIBRARY.filter((text) => !hiddenSet.has(text))
    ])].slice(0, 80);
  }

  function getReplyLibrary() {
    const analytics = loadReplyAnalytics();
    return analytics.list?.length ? analytics.list : [...DEFAULT_REPLY_LIBRARY];
  }

  function getReplyLibraryMeta() {
    const analytics = loadReplyAnalytics();
    return `内置 ${DEFAULT_REPLY_LIBRARY.length} 条 当前 ${analytics.list.length} 条回复`;
  }

  function addReplyToLibrary(replyText) {
    const nextReply = normalizeReplyCandidate(replyText);
    if (!isUsefulReplyCandidate(nextReply)) {
      return false;
    }

    const analytics = loadReplyAnalytics();
    const hiddenSet = new Set(analytics.hiddenReplies || []);
    hiddenSet.delete(nextReply);
    analytics.hiddenReplies = [...hiddenSet];
    analytics.customReplies = [...new Set([...(analytics.customReplies || []), nextReply])];
    analytics.list = buildReplyLibrary(analytics.freq, analytics.hiddenReplies, analytics.customReplies);
    analytics.updatedAt = Date.now();
    saveReplyAnalytics(analytics);
    return true;
  }

  function updateReplyInLibrary(oldReplyText, nextReplyText) {
    const oldReply = normalizeReplyCandidate(oldReplyText);
    const nextReply = normalizeReplyCandidate(nextReplyText);
    if (!oldReply || !isUsefulReplyCandidate(nextReply)) {
      return false;
    }

    const analytics = loadReplyAnalytics();
    const hiddenSet = new Set(analytics.hiddenReplies || []);
    hiddenSet.delete(nextReply);
    hiddenSet.add(oldReply);
    delete analytics.freq[oldReply];
    analytics.hiddenReplies = [...hiddenSet];
    analytics.customReplies = (analytics.customReplies || [])
      .map((text) => normalizeReplyCandidate(text))
      .filter((text) => text && text !== oldReply);
    analytics.customReplies.push(nextReply);
    analytics.customReplies = [...new Set(analytics.customReplies)];
    analytics.list = buildReplyLibrary(analytics.freq, analytics.hiddenReplies, analytics.customReplies);
    analytics.updatedAt = Date.now();
    saveReplyAnalytics(analytics);
    return true;
  }

  function deleteReplyFromLibrary(replyText) {
    const normalizedReply = normalizeReplyCandidate(replyText);
    if (!normalizedReply) {
      return;
    }
    const analytics = loadReplyAnalytics();
    const hiddenSet = new Set(analytics.hiddenReplies || []);
    hiddenSet.add(normalizedReply);
    delete analytics.freq[normalizedReply];
    analytics.customReplies = (analytics.customReplies || [])
      .map((text) => normalizeReplyCandidate(text))
      .filter((text) => text && text !== normalizedReply);
    analytics.hiddenReplies = [...hiddenSet];
    analytics.list = buildReplyLibrary(analytics.freq, analytics.hiddenReplies, analytics.customReplies);
    analytics.updatedAt = Date.now();
    saveReplyAnalytics(analytics);
  }

  function buildReplyDraft(title, seed) {
    const pool = getReplyLibrary();
    return pool[Math.abs(seed) % pool.length] || DEFAULT_REPLY_LIBRARY[0];
  }

  function fillReplyDraft(seed) {
    const textarea = getReplyTextarea();
    if (!textarea) {
      return '';
    }

    const draft = buildReplyDraft(getThreadTitle(), seed);
    textarea.value = draft;
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.dispatchEvent(new Event('change', { bubbles: true }));
    return draft;
  }

  function dockReplyHelperToRight(panel) {
    const rect = panel.getBoundingClientRect();
    const nextTop = Math.min(
      Math.max(8, rect.top),
      Math.max(8, window.innerHeight - panel.offsetHeight - 8)
    );
    panel.classList.add('is-docked-right');
    panel.style.left = 'auto';
    panel.style.right = '12px';
    panel.style.top = `${nextTop}px`;
    panel.style.bottom = 'auto';
  }

  function keepReplyHelperInViewport(panel) {
    const rect = panel.getBoundingClientRect();
    const nextTop = Math.min(
      Math.max(8, rect.top),
      Math.max(8, window.innerHeight - panel.offsetHeight - 8)
    );
    if (panel.classList.contains('is-docked-right')) {
      panel.style.left = 'auto';
      panel.style.right = '12px';
    }
    panel.style.top = `${nextTop}px`;
    panel.style.bottom = 'auto';
  }

  function makeReplyHelperDraggable(panel, handle, onToggle) {
    let dragState = null;

    const move = (clientX, clientY) => {
      if (!dragState) {
        return;
      }

      if (Math.abs(clientX - dragState.startX) > 4 || Math.abs(clientY - dragState.startY) > 4) {
        dragState.moved = true;
      }

      const nextLeft = Math.min(
        Math.max(8, clientX - dragState.offsetX),
        Math.max(8, window.innerWidth - panel.offsetWidth - 8)
      );
      const nextTop = Math.min(
        Math.max(8, clientY - dragState.offsetY),
        Math.max(8, window.innerHeight - panel.offsetHeight - 8)
      );

      panel.classList.remove('is-docked-right');
      panel.style.left = `${nextLeft}px`;
      panel.style.top = `${nextTop}px`;
      panel.style.right = 'auto';
      panel.style.bottom = 'auto';
    };

    const stopDrag = () => {
      const moved = dragState?.moved;
      dragState = null;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', stopDrag);
      document.removeEventListener('touchmove', onTouchMove);
      document.removeEventListener('touchend', stopDrag);
      if (!moved && typeof onToggle === 'function') {
        onToggle();
      }
    };

    const onMouseMove = (event) => move(event.clientX, event.clientY);
    const onTouchMove = (event) => {
      const touch = event.touches[0];
      if (!touch) {
        return;
      }
      move(touch.clientX, touch.clientY);
    };

    const startDrag = (clientX, clientY) => {
      const rect = panel.getBoundingClientRect();
      dragState = {
        startX: clientX,
        startY: clientY,
        moved: false,
        offsetX: clientX - rect.left,
        offsetY: clientY - rect.top
      };
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', stopDrag);
      document.addEventListener('touchmove', onTouchMove, { passive: true });
      document.addEventListener('touchend', stopDrag);
    };

    handle.addEventListener('mousedown', (event) => {
      startDrag(event.clientX, event.clientY);
    });

    handle.addEventListener('touchstart', (event) => {
      const touch = event.touches[0];
      if (!touch) {
        return;
      }
      startDrag(touch.clientX, touch.clientY);
    }, { passive: true });
  }

  function addReplyHelper() {
    const textarea = getReplyTextarea();
    if (!textarea || document.querySelector('.reply-helper')) {
      return;
    }

    let seed = Math.floor(Math.random() * 100000);
    let isNoImage = document.body.classList.contains('cl-no-image');
    let isCollapsed = false;
    const panel = document.createElement('div');
    panel.className = 'reply-helper is-docked-right';
    panel.innerHTML = `
      <div class="reply-helper-title">回复草稿</div>
      <div class="reply-helper-meta"></div>
      <div class="reply-helper-draft"></div>
      <div class="reply-helper-row">
        <button type="button" class="reply-helper-btn" data-action="fill">回复</button>
        <button type="button" class="reply-helper-btn" data-action="next">换一句</button>
        <button type="button" class="reply-helper-btn" data-action="list">List</button>
      </div>
      <div class="reply-helper-row">
        <button type="button" class="reply-helper-btn" data-action="download">下载</button>
        <button type="button" class="reply-helper-btn" data-action="no-image">无图</button>
        <button type="button" class="reply-helper-btn" data-action="auto-reply-toggle"></button>
      </div>
      <div class="reply-helper-list"></div>
    `;
    document.body.appendChild(panel);

    const titleNode = panel.querySelector('.reply-helper-title');
    const metaNode = panel.querySelector('.reply-helper-meta');
    const draftNode = panel.querySelector('.reply-helper-draft');
    const listNode = panel.querySelector('.reply-helper-list');
    const noImageBtn = panel.querySelector('[data-action="no-image"]');
    const listBtn = panel.querySelector('[data-action="list"]');
    const autoReplyToggleBtn = panel.querySelector('[data-action="auto-reply-toggle"]');

    const renderList = () => {
      const replies = getReplyLibrary();
      if (!replies.length) {
        listNode.innerHTML = `
          <div class="reply-helper-list-tools">
            <input type="text" class="reply-helper-list-input" data-role="new-reply-input" placeholder="自定义回复">
          </div>
          <div class="reply-helper-list-empty">暂无回复</div>
        `;
        return;
      }

      listNode.innerHTML = `
        <div class="reply-helper-list-tools">
          <input type="text" class="reply-helper-list-input" data-role="new-reply-input" placeholder="自定义回复">
        </div>
        ${replies.map((reply) => `
        <div class="reply-helper-list-row">
          <div class="reply-helper-list-text" data-reply="${escapeHtml(reply)}">${escapeHtml(reply)}</div>
          <button type="button" class="reply-helper-list-del" data-delete-reply="${escapeHtml(reply)}">删</button>
        </div>
      `).join('')}
      `;
    };

    const renderDraft = () => {
      metaNode.textContent = getReplyLibraryMeta();
      draftNode.textContent = buildReplyDraft(getThreadTitle(), seed);
      noImageBtn.classList.toggle('is-active', isNoImage);
      listBtn.classList.toggle('is-active', listNode.classList.contains('is-open'));
      autoReplyToggleBtn.textContent = isAutoReplyEnabled() ? '自回开' : '自回关';
      autoReplyToggleBtn.classList.toggle('is-active', isAutoReplyEnabled());
      panel.classList.toggle('is-collapsed', isCollapsed);
      requestAnimationFrame(() => keepReplyHelperInViewport(panel));
    };

    makeReplyHelperDraggable(panel, titleNode, () => {
      isCollapsed = !isCollapsed;
      dockReplyHelperToRight(panel);
      renderDraft();
    });
    renderList();
    renderDraft();
    requestAnimationFrame(() => dockReplyHelperToRight(panel));
    window.addEventListener('resize', () => {
      if (panel.classList.contains('is-docked-right')) {
        dockReplyHelperToRight(panel);
        return;
      }
      keepReplyHelperInViewport(panel);
    });

    const finishInlineEdit = (textNode, saveChanges) => {
      if (!textNode || textNode.contentEditable !== 'true') {
        return;
      }
      const originalReply = textNode.dataset.originalReply || textNode.dataset.reply || '';
      const nextReply = normalizeReplyCandidate(textNode.textContent || '');
      textNode.contentEditable = 'false';
      textNode.classList.remove('is-editing');
      delete textNode.dataset.originalReply;

      if (!saveChanges || !nextReply || nextReply === originalReply) {
        textNode.textContent = originalReply;
        textNode.dataset.reply = originalReply;
        return;
      }

      if (updateReplyInLibrary(originalReply, nextReply)) {
        renderList();
        renderDraft();
      } else {
        textNode.textContent = originalReply;
        textNode.dataset.reply = originalReply;
      }
    };

    panel.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-action]');
      const deleteBtn = event.target.closest('[data-delete-reply]');
      if (deleteBtn) {
        deleteReplyFromLibrary(deleteBtn.getAttribute('data-delete-reply') || '');
        renderList();
        renderDraft();
        return;
      }

      if (!btn) {
        return;
      }
      const action = btn.getAttribute('data-action');
      if (action === 'fill') {
        fillReplyDraft(seed);
        textarea.focus();
      }
      if (action === 'next') {
        seed += 1;
        renderDraft();
      }
      if (action === 'download') {
        batchDownloadImages();
      }
      if (action === 'no-image') {
        isNoImage = !isNoImage;
        document.body.classList.toggle('cl-no-image', isNoImage);
        renderDraft();
      }
      if (action === 'auto-reply-toggle') {
        setAutoReplyEnabled(!isAutoReplyEnabled());
        renderDraft();
      }
      if (action === 'list') {
        listNode.classList.toggle('is-open');
        renderDraft();
      }
    });

    panel.addEventListener('dblclick', (event) => {
      const textNode = event.target.closest('.reply-helper-list-text');
      if (!textNode || textNode.contentEditable === 'true') {
        return;
      }
      const reply = textNode.dataset.reply || textNode.textContent || '';
      textNode.dataset.originalReply = reply;
      textNode.contentEditable = 'true';
      textNode.classList.add('is-editing');
      textNode.focus();
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(textNode);
      selection.removeAllRanges();
      selection.addRange(range);
    });

    panel.addEventListener('keydown', (event) => {
      const editingTextNode = event.target.closest('.reply-helper-list-text');
      if (editingTextNode && editingTextNode.contentEditable === 'true') {
        if (event.key === 'Enter') {
          event.preventDefault();
          finishInlineEdit(editingTextNode, true);
        }
        if (event.key === 'Escape') {
          event.preventDefault();
          finishInlineEdit(editingTextNode, false);
        }
        return;
      }

      const input = event.target.closest('[data-role="new-reply-input"]');
      if (input && event.key === 'Enter') {
        event.preventDefault();
        if (addReplyToLibrary(input.value || '')) {
          input.value = '';
          renderList();
          renderDraft();
        }
      }
    });

    panel.addEventListener('focusout', (event) => {
      const editingTextNode = event.target.closest('.reply-helper-list-text');
      if (editingTextNode && editingTextNode.contentEditable === 'true') {
        finishInlineEdit(editingTextNode, true);
      }
    });

    if (!textarea.value.trim()) {
      fillReplyDraft(seed);
    }
  }

  const READ_THREADS_KEY = 'cl1024-read-threads-v1';
  const AUTO_LIKED_THREADS_KEY = 'cl1024-auto-liked-threads-v1';
  const AUTO_REPLIED_THREADS_KEY = 'cl1024-auto-replied-threads-v1';
  const AUTO_REPLY_ENABLED_KEY = 'cl1024-auto-reply-enabled-v1';

  function isAutoReplyEnabled() {
    return localStorage.getItem(AUTO_REPLY_ENABLED_KEY) !== '0';
  }

  function setAutoReplyEnabled(enabled) {
    localStorage.setItem(AUTO_REPLY_ENABLED_KEY, enabled ? '1' : '0');
  }

  function loadReadThreads() {
    try {
      return JSON.parse(localStorage.getItem(READ_THREADS_KEY) || '{}');
    } catch (error) {
      return {};
    }
  }

  function saveReadThreads(data) {
    localStorage.setItem(READ_THREADS_KEY, JSON.stringify(data));
  }

  function loadAutoLikedThreads() {
    try {
      return JSON.parse(localStorage.getItem(AUTO_LIKED_THREADS_KEY) || '{}');
    } catch (error) {
      return {};
    }
  }

  function saveAutoLikedThreads(data) {
    localStorage.setItem(AUTO_LIKED_THREADS_KEY, JSON.stringify(data));
  }

  function loadAutoRepliedThreads() {
    try {
      return JSON.parse(localStorage.getItem(AUTO_REPLIED_THREADS_KEY) || '{}');
    } catch (error) {
      return {};
    }
  }

  function saveAutoRepliedThreads(data) {
    localStorage.setItem(AUTO_REPLIED_THREADS_KEY, JSON.stringify(data));
  }

  function extractThreadId(url) {
    if (!url) {
      return null;
    }

    const tidMatch = url.match(/[?&]tid=(\d+)/i);
    if (tidMatch) {
      return tidMatch[1];
    }

    const htmlMatch = url.match(/\/(\d+)\.html(?:$|[?#])/);
    if (htmlMatch) {
      return htmlMatch[1];
    }

    const readMatch = url.match(/read\.php.*(?:tid=|\/)(\d+)/i);
    if (readMatch) {
      return readMatch[1];
    }

    return null;
  }

  function markCurrentThreadAsRead() {
    const tid = extractThreadId(window.location.href);
    if (!tid) {
      return;
    }

    const readThreads = loadReadThreads();
    readThreads[tid] = Date.now();
    saveReadThreads(readThreads);
  }

  function autoLikeCurrentThread() {
    if (!document.querySelector('#conttpc')) {
      return;
    }

    const tid = extractThreadId(window.location.href) || window.location.href;
    const autoLikedThreads = loadAutoLikedThreads();
    if (autoLikedThreads[tid]) {
      return;
    }

    const tryClick = (retries = 12) => {
      const likeBtn = [...document.querySelectorAll('.t_like[id^="like"], [onclick*="clickLike"]')]
        .find((node) => /clickLike\(/.test(node.getAttribute('onclick') || ''));

      if (!likeBtn) {
        if (retries > 0) {
          setTimeout(() => tryClick(retries - 1), 800);
        }
        return;
      }

      likeBtn.click();
      autoLikedThreads[tid] = Date.now();
      saveAutoLikedThreads(autoLikedThreads);
    };

    tryClick();
  }

  function autoReplyCurrentThread() {
    if (!isAutoReplyEnabled()) {
      return;
    }

    if (!document.querySelector('#conttpc') || !isAutoReplyAllowedForum()) {
      return;
    }

    const tid = extractThreadId(window.location.href) || window.location.href;
    const autoRepliedThreads = loadAutoRepliedThreads();
    if (autoRepliedThreads[tid]) {
      return;
    }

    const trySubmit = (retries = 12) => {
      const textarea = getReplyTextarea();
      const submitBtn = document.querySelector('form[name="FORM"] input[type="submit"][name="Submit"], input[type="submit"][name="Submit"]');
      const titleInput = document.querySelector('form[name="FORM"] input[name="atc_title"]');

      if (!textarea || !submitBtn || !titleInput) {
        if (retries > 0) {
          setTimeout(() => trySubmit(retries - 1), 800);
        }
        return;
      }

      if (!textarea.value.trim()) {
        fillReplyDraft(Math.floor(Math.random() * 100000));
      }

      if (!textarea.value.trim()) {
        return;
      }

      const replyText = textarea.value.trim();
      const delay = randomBetween(AUTO_REPLY_DELAY_MIN, AUTO_REPLY_DELAY_MAX);
      setTimeout(() => {
        if (!isAutoReplyEnabled()) {
          return;
        }
        autoRepliedThreads[tid] = {
          text: replyText,
          title: titleInput.value || '',
          submittedAt: Date.now(),
          forumId: getCurrentForumId()
        };
        saveAutoRepliedThreads(autoRepliedThreads);
        submitBtn.click();
      }, delay);
    };

    trySubmit();
  }

  function highlightUnreadThreads() {
    const readThreads = loadReadThreads();
    const links = document.querySelectorAll('a[href*="read.php"], a[href*="/htm_data/"]');

    links.forEach((link) => {
      const tid = extractThreadId(link.href);
      if (!tid) {
        return;
      }

      if (readThreads[tid]) {
        return;
      }

      const row = link.closest('tr, li, h3, .tr3, .tr2, .t_one, .subject');
      if (row) {
        row.classList.add('newPost');
      } else {
        link.classList.add('newPost');
      }
    });
  }

  function init() {
    if (handlePromptPages()) {
      addBackToTop();
      return;
    }
    reloadImageUrls();
    highlightUnreadThreads();
    markCurrentThreadAsRead();
    autoLikeCurrentThread();
    autoReplyCurrentThread();
    addBackToTop();
    addReplyHelper();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
