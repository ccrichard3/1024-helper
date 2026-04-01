// ==UserScript==
// @name         1024回复采样器
// @namespace    https://greasyfork.org/zh-CN/scripts/489614-1024%E5%B0%8F%E5%8A%A9%E6%89%8B
// @version      1.0
// @description  独立后台采样草榴回复库，控制请求频率并共享给 1024小助手 使用
// @author       cc
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
// @run-at       document-idle
// @license      MIT License
// ==/UserScript==

(function () {
  'use strict';

  const REPLY_ANALYTICS_KEY = 'cl1024-reply-analytics-v1';
  const REPLY_SAMPLER_STATE_KEY = 'cl1024-reply-sampler-state-v1';
  const REPLY_SAMPLE_TARGET = 200;
  const REPLY_FORUM_IDS = [2, 15];
  const REPLY_FORUM_PAGES = 2;
  const AUTO_REPLY_ALLOWED_FORUM_IDS = new Set(REPLY_FORUM_IDS);
  const SAMPLER_REQUEST_DELAY_MIN = 5000;
  const SAMPLER_REQUEST_DELAY_MAX = 60000;
  const SAMPLER_RUN_COOLDOWN_MIN = 25 * 60 * 1000;
  const SAMPLER_RUN_COOLDOWN_MAX = 70 * 60 * 1000;
  const SAMPLER_BLOCK_COOLDOWN = 12 * 60 * 60 * 1000;
  const SAMPLER_REFRESH_STALE_MS = 12 * 60 * 60 * 1000;
  const PROCESSED_THREAD_TTL = 12 * 60 * 60 * 1000;
  const TICK_INTERVAL = 60 * 1000;
  const DEFAULT_REPLY_LIBRARY = [
    '这个帖子挺实用 收下了',
    '楼主发帖辛苦 支持一下',
    '支持优质内容 感谢更新',
    '帖子看着很顺 感谢分享',
    '整理得很省事 支持',
    '质量在线 先回再看',
    '这帖不错 收藏慢慢看',
    '分享很及时 支持一下',
    '内容挺全 感谢整理分享'
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

  function randomBetween(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
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
      const list = [...new Set(
        (Array.isArray(data.list) && data.list.length ? data.list : [...customReplies, ...DEFAULT_REPLY_LIBRARY])
          .map((text) => normalizeReplyCandidate(text))
          .filter((text) => text && !REMOVED_REPLY_LIBRARY.has(text) && !hiddenSet.has(text))
      )];
      return {
        ...createReplyAnalytics(),
        ...data,
        threadCount: Object.keys(processedThreads).length,
        processedThreads,
        freq,
        customReplies,
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

  function createReplySamplerState() {
    return {
      nextRunAt: 0,
      blockedUntil: 0,
      lastStatus: 'idle',
      updatedAt: Date.now()
    };
  }

  function loadReplySamplerState() {
    try {
      const data = JSON.parse(localStorage.getItem(REPLY_SAMPLER_STATE_KEY) || 'null');
      if (!data || typeof data !== 'object') {
        return createReplySamplerState();
      }
      return {
        ...createReplySamplerState(),
        ...data
      };
    } catch (error) {
      return createReplySamplerState();
    }
  }

  function updateReplySamplerState(patch) {
    const nextState = {
      ...loadReplySamplerState(),
      ...patch,
      updatedAt: Date.now()
    };
    localStorage.setItem(REPLY_SAMPLER_STATE_KEY, JSON.stringify(nextState));
    return nextState;
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

  function extractReplyCandidatesFromRoot(root) {
    const seen = new Set();
    return [...root.querySelectorAll('.tpc_content[id^="cont"]')]
      .map((node) => normalizeReplyCandidate(node.textContent || ''))
      .filter((text) => {
        if (!isUsefulReplyCandidate(text) || seen.has(text)) {
          return false;
        }
        seen.add(text);
        return true;
      })
      .slice(0, 12);
  }

  function mergeReplyCandidates(threadId, replies) {
    if (!threadId || !replies.length) {
      return false;
    }

    const analytics = loadReplyAnalytics();
    if (analytics.processedThreads[threadId]) {
      return false;
    }

    replies.forEach((reply) => {
      analytics.freq[reply] = (analytics.freq[reply] || 0) + 1;
    });
    analytics.processedThreads[threadId] = Date.now();
    analytics.threadCount = Object.keys(analytics.processedThreads).length;
    analytics.replyCount += replies.length;
    analytics.list = buildReplyLibrary(analytics.freq, analytics.hiddenReplies, analytics.customReplies);
    analytics.updatedAt = Date.now();
    saveReplyAnalytics(analytics);
    return true;
  }

  function collectReplySamplesFromCurrentPage() {
    if (!document.querySelector('#conttpc')) {
      return;
    }

    const fid = getCurrentForumId();
    if (fid == null || !AUTO_REPLY_ALLOWED_FORUM_IDS.has(fid)) {
      return;
    }

    const tid = extractThreadId(window.location.href);
    if (!tid) {
      return;
    }

    mergeReplyCandidates(tid, extractReplyCandidatesFromRoot(document));
  }

  async function fetchDocument(url) {
    try {
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) {
        return {
          ok: false,
          status: response.status,
          doc: null
        };
      }
      const html = await response.text();
      return {
        ok: true,
        status: response.status,
        doc: new DOMParser().parseFromString(html, 'text/html')
      };
    } catch (error) {
      return {
        ok: false,
        status: 0,
        doc: null
      };
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function resolveUrl(path) {
    return new URL(path, window.location.origin).href;
  }

  function getSamplerRunPlan(threadCount) {
    if (threadCount < 20) {
      return { forumPages: 1, threads: 2 };
    }
    if (threadCount < 80) {
      return { forumPages: 1, threads: 3 };
    }
    return { forumPages: 2, threads: 4 };
  }

  function extractThreadLinksFromForumDoc(doc) {
    const links = [];
    const seen = new Set();

    doc.querySelectorAll('#ajaxtable h3 a[href], h3 a[href*="htm_data/"], h3 a[href*="read.php?tid="]').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href) {
        return;
      }

      const full = resolveUrl(href);
      const tid = extractThreadId(full);
      if (!tid || seen.has(tid)) {
        return;
      }

      seen.add(tid);
      links.push(full);
    });

    return links;
  }

  let isReplySamplerRunning = false;

  async function warmReplyLibraryFromSite() {
    if (isReplySamplerRunning) {
      return;
    }

    const current = loadReplyAnalytics();
    const now = Date.now();
    const isLibraryStale = now - (Number(current.updatedAt) || 0) > SAMPLER_REFRESH_STALE_MS;
    const allowRefreshRun = isLibraryStale;
    if (current.threadCount >= REPLY_SAMPLE_TARGET && !allowRefreshRun) {
      return;
    }

    const samplerState = loadReplySamplerState();
    if (samplerState.blockedUntil > now || samplerState.nextRunAt > now) {
      return;
    }

    isReplySamplerRunning = true;
    try {
      const runPlan = getSamplerRunPlan(current.threadCount);
      const queue = [];
      const queueSeen = new Set();
      let scannedForumPages = 0;
      let scannedThreads = 0;

      for (const fid of REPLY_FORUM_IDS) {
        for (let page = 1; page <= REPLY_FORUM_PAGES; page += 1) {
          const latest = loadReplyAnalytics();
          if ((latest.threadCount >= REPLY_SAMPLE_TARGET && !allowRefreshRun) || scannedForumPages >= runPlan.forumPages) {
            return;
          }

          const forumUrl = `/thread0806.php?fid=${fid}${page > 1 ? `&page=${page}` : ''}`;
          const forumResult = await fetchDocument(forumUrl);
          if (!forumResult.ok) {
            if (forumResult.status === 403) {
              updateReplySamplerState({
                blockedUntil: Date.now() + SAMPLER_BLOCK_COOLDOWN,
                nextRunAt: Date.now() + SAMPLER_BLOCK_COOLDOWN,
                lastStatus: '403'
              });
              return;
            }
            continue;
          }
          scannedForumPages += 1;

          extractThreadLinksFromForumDoc(forumResult.doc).forEach((link) => {
            const tid = extractThreadId(link);
            if (!tid || queueSeen.has(tid)) {
              return;
            }
            queueSeen.add(tid);
            queue.push(link);
          });

          await sleep(randomBetween(SAMPLER_REQUEST_DELAY_MIN, SAMPLER_REQUEST_DELAY_MAX));
        }
      }

      for (const link of queue) {
        const latest = loadReplyAnalytics();
        if ((latest.threadCount >= REPLY_SAMPLE_TARGET && !allowRefreshRun) || scannedThreads >= runPlan.threads) {
          break;
        }

        const tid = extractThreadId(link);
        if (!tid || latest.processedThreads[tid]) {
          continue;
        }

        const threadResult = await fetchDocument(link);
        if (!threadResult.ok) {
          if (threadResult.status === 403) {
            updateReplySamplerState({
              blockedUntil: Date.now() + SAMPLER_BLOCK_COOLDOWN,
              nextRunAt: Date.now() + SAMPLER_BLOCK_COOLDOWN,
              lastStatus: '403'
            });
            return;
          }
          continue;
        }

        mergeReplyCandidates(tid, extractReplyCandidatesFromRoot(threadResult.doc));
        scannedThreads += 1;
        await sleep(randomBetween(SAMPLER_REQUEST_DELAY_MIN, SAMPLER_REQUEST_DELAY_MAX));
      }

      updateReplySamplerState({
        nextRunAt: Date.now() + randomBetween(SAMPLER_RUN_COOLDOWN_MIN, SAMPLER_RUN_COOLDOWN_MAX),
        blockedUntil: 0,
        lastStatus: 'ok'
      });
    } finally {
      isReplySamplerRunning = false;
    }
  }

  function startSamplerLoop() {
    collectReplySamplesFromCurrentPage();
    setTimeout(() => {
      warmReplyLibraryFromSite();
      setInterval(() => {
        warmReplyLibraryFromSite();
      }, TICK_INTERVAL);
    }, randomBetween(3000, 9000));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startSamplerLoop);
  } else {
    startSamplerLoop();
  }
})();
