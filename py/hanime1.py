# coding=utf-8
# hanime1.py —— TVBox / FongMi Python 爬虫
import re
import sys
import urllib.parse

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    host = 'https://hanime1.me'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://hanime1.me/',
        'Accept-Language': 'zh-TW,zh;q=0.9,zh-CN;q=0.8',
    }

    cates = [
        ('最新里番', 'genre_sort:裏番|最新上市'),
        ('最新上市', 'sort:最新上市'),
        ('最新上传', 'sort:最新上傳'),
        ('里番', '裏番'),
        ('泡面番', '泡麵番'),
        ('Motion Anime', 'Motion Anime'),
        ('3DCG', '3DCG'),
        ('2.5D', '2.5D'),
        ('2D动画', '2D動畫'),
        ('AI生成', 'AI生成'),
        ('MMD', 'MMD'),
        ('Cosplay', 'Cosplay'),
        ('新番预告', '新番預告'),
    ]

    sorts = [
        {'n': '最新上市', 'v': '最新上市'},
        {'n': '最新上传', 'v': '最新上傳'},
        {'n': '本日排行', 'v': '本日排行'},
        {'n': '本周排行', 'v': '本週排行'},
        {'n': '本月排行', 'v': '本月排行'},
    ]

    # ---------- 基础 ----------
    def getName(self):
        return 'hanime1'

    def init(self, extend=''):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        return None

    def _get(self, url):
        try:
            return self.fetch(url, headers=self.headers, timeout=15).text
        except Exception:
            import requests
            return requests.get(url, headers=self.headers, timeout=15).text

    def _meta(self, html, prop):
        m = re.search(r'<meta[^>]+property="%s"[^>]+content="([^"]*)"' % prop, html)
        if not m:
            m = re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="%s"' % prop, html)
        return m.group(1).strip() if m else ''

    # ---------- 列表解析 ----------
    def parse_list(self, html):
        videos = []
        seen = set()

        card_pattern = re.compile(
            r'<a[^>]+href=["\'](?:https?://hanime1\.me)?/watch\?v=(\d+)["\'][^>]*>(.*?)</a>',
            re.S
        )

        for m in card_pattern.finditer(html):
            vid = m.group(1)
            if vid in seen:
                continue
            inner = m.group(2)

            title = ''
            t = re.search(
                r'class="[^"]*(?:title|name)[^"]*"[^>]*>\s*([^<]+?)\s*<',
                inner, re.S
            )
            if t:
                title = t.group(1).strip()
            if not title:
                t = re.search(r'<img[^>]+alt="([^"]+)"', inner)
                if t:
                    title = t.group(1).strip()
            if not title:
                t = re.search(r'title="([^"]+)"', m.group(0))
                if t:
                    title = t.group(1).strip()
            if not title:
                continue

            pic = ''
            for img in re.findall(r'<img[^>]+(?:data-src|src)="(http[^"]+)"', inner):
                if '.gif' in img or 'icon' in img or 'avatar' in img:
                    continue
                pic = img
                break

            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': ''
            })

        if not videos:
            videos = self._parse_list_fallback(html)
        return videos

    def _parse_list_fallback(self, html):
        videos = []
        seen = set()
        for m in re.finditer(
            r'<a[^>]+href=["\'][^"\']*watch\?v=(\d+)["\']([^>]*)>(.*?)</a>',
            html, re.S
        ):
            vid = m.group(1)
            if vid in seen:
                continue
            attrs = m.group(2)
            inner = m.group(3)
            t = re.search(r'title="([^"]+)"', attrs)
            title = t.group(1).strip() if t else ''
            if not title:
                title = re.sub(r'<[^>]+>', '', inner).strip()
            if not title:
                continue
            seen.add(vid)
            videos.append({'vod_id': vid, 'vod_name': title, 'vod_pic': '', 'vod_remarks': ''})
        return videos

    # ---------- 首页 ----------
    def homeContent(self, filter):
        classes = [{'type_name': n, 'type_id': v} for n, v in self.cates]
        filters = {}
        for _, v in self.cates:
            if not v.startswith('sort:') and not v.startswith('genre_sort:'):
                filters[v] = [{'key': 'sort', 'name': '排序', 'value': self.sorts}]
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        html = self._get(self.host)
        return {'list': self.parse_list(html)[:30]}

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        if tid.startswith('genre_sort:'):
            parts = tid[len('genre_sort:'):].split('|', 1)
            genre = parts[0]
            sort  = parts[1] if len(parts) > 1 else ''
            url = '{}/search?genre={}&page={}'.format(
                self.host, urllib.parse.quote(genre), pg)
            if sort:
                url += '&sort=' + urllib.parse.quote(sort)
        elif tid.startswith('sort:'):
            sort_val = tid[len('sort:'):]
            url = '{}/search?sort={}&page={}'.format(
                self.host, urllib.parse.quote(sort_val), pg)
        else:
            url = '{}/search?genre={}&page={}'.format(
                self.host, urllib.parse.quote(tid), pg)
            if extend and extend.get('sort'):
                url += '&sort=' + urllib.parse.quote(extend['sort'])

        html = self._get(url)
        videos = self.parse_list(html)
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': int(pg) + (1 if len(videos) >= 20 else 0),
            'limit': 30,
            'total': 999999
        }

    # ---------- 详情 ----------
    def detailContent(self, ids):
        vid = ids[0]
        html = self._get('{}/watch?v={}'.format(self.host, vid))

        title = self._meta(html, 'og:title')
        pic   = self._meta(html, 'og:image')
        desc  = self._meta(html, 'og:description')

        episodes = self._extract_playlist(html, vid, title)

        # ✅ 修复：将集数名称中的 # 替换为全角 ＃，避免与分隔符冲突
        def safe_ep_name(name):
            return name.replace('#', '＃')

        play_url = '#'.join(
            '{}${}'.format(safe_ep_name(ep['name']), ep['vid'])
            for ep in episodes
        )

        vod = {
            'vod_id'       : vid,
            'vod_name'     : title,
            'vod_pic'      : pic,
            'vod_content'  : desc,
            'vod_play_from': 'Hanime1',
            'vod_play_url' : play_url,
        }
        return {'list': [vod]}

    def _extract_playlist(self, html, current_vid, current_title):
        """
        多策略提取播放列表，兼容 hanime1.me 各种页面结构
        """
        episodes = []
        seen = set()

        # ── 策略1：标准选集区块（playlist / related 区域内的 watch 链接）──
        playlist_html = ''
        for block_pat in [
            r'(?:id|class)="[^"]*(?:playlist|episodes?|series|related|同系列|選集)[^"]*"[^>]*>(.*?)(?=<(?:div|section|aside)[^>]+(?:id|class)="[^"]*(?:comment|footer|recommend|sidebar))',
            r'(?:playlist|episodes?|series)[^>]*>(.*?)(?=</(?:div|section|ul)>)',
        ]:
            bm = re.search(block_pat, html, re.S | re.I)
            if bm:
                playlist_html = bm.group(1)
                break

        if playlist_html:
            for m in re.finditer(r'href="[^"]*watch\?v=(\d+)"[^>]*>([^<]*)<', playlist_html):
                ep_vid  = m.group(1)
                ep_name = m.group(2).strip()
                if ep_vid not in seen and ep_name:
                    seen.add(ep_vid)
                    episodes.append({'name': ep_name, 'vid': ep_vid})

        # ── 策略2：原正则（card-mobile-panel 结构）──
        if not episodes:
            ep_pattern = re.compile(
                r'href="https?://hanime1\.me/watch\?v=(\d+)"'
                r'.*?'
                r'class="card-mobile-title"[^>]*>\s*([^<]+?)\s*<',
                re.S
            )
            for m in ep_pattern.finditer(html):
                ep_vid  = m.group(1)
                ep_name = m.group(2).strip()
                if ep_vid not in seen and ep_name:
                    seen.add(ep_vid)
                    episodes.append({'name': ep_name, 'vid': ep_vid})

        # ── 策略3：宽松匹配——找所有 watch?v=xxx 链接，取其最近的文本节点 ──
        if not episodes:
            for m in re.finditer(
                r'<a[^>]+href="[^"]*watch\?v=(\d+)"[^>]*>\s*([^<]{1,60}?)\s*</a>',
                html, re.S
            ):
                ep_vid  = m.group(1)
                ep_name = m.group(2).strip()
                if not ep_name or ep_name in ('', '\n'):
                    continue
                if ep_vid not in seen:
                    seen.add(ep_vid)
                    episodes.append({'name': ep_name, 'vid': ep_vid})

        # ── 策略4：最后兜底——用 data-v 或 data-id 属性 ──
        if not episodes:
            for m in re.finditer(
                r'data-(?:v|id|video-id)="(\d+)"[^>]*data-(?:title|name)="([^"]+)"',
                html
            ):
                ep_vid  = m.group(1)
                ep_name = m.group(2).strip()
                if ep_vid not in seen:
                    seen.add(ep_vid)
                    episodes.append({'name': ep_name, 'vid': ep_vid})

        # ── 所有策略失败，返回当前集 ──
        if not episodes:
            return [{'name': current_title or current_vid, 'vid': current_vid}]

        # 确保当前集在列表里
        if not any(e['vid'] == current_vid for e in episodes):
            episodes.insert(0, {'name': current_title or current_vid, 'vid': current_vid})

        # 按集数数字升序排序
        def _ep_num(ep):
            m = re.search(r'(\d+)\s*$', ep['name'])
            return int(m.group(1)) if m else 0

        try:
            episodes.sort(key=_ep_num)
        except Exception:
            pass

        # 把当前集挪到最前面
        cur_idx = next((i for i, e in enumerate(episodes) if e['vid'] == current_vid), None)
        if cur_idx is not None and cur_idx != 0:
            cur_ep = episodes.pop(cur_idx)
            episodes.insert(0, cur_ep)

        return episodes

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        url = '{}/search?query={}&page={}'.format(
            self.host, urllib.parse.quote(key), pg)
        html = self._get(url)
        return {'list': self.parse_list(html), 'page': int(pg)}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        # ✅ 修复：清洗 id，防止含有 # 残留导致 URL 构造错误
        vid = id.split('#')[0].strip()

        html = self._get('{}/watch?v={}'.format(self.host, vid))
        play = ''

        # 优先取最高清晰度的 <source>
        sources = re.findall(r'<source[^>]+src="([^"]+)"[^>]*size="(\d+)"', html)
        if sources:
            sources.sort(key=lambda x: int(x[1]), reverse=True)
            play = sources[0][0]

        # JSON-LD contentUrl
        if not play:
            m = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', html)
            if m:
                play = m.group(1).replace('\\/', '/')

        # 裸链接
        if not play:
            m = re.search(r'(https?://[^\s\'"]+\.(?:m3u8|mp4)[^\s\'"]*)', html)
            if m:
                play = m.group(1)

        return {
            'parse': 0 if play else 1,
            'url'  : play or '{}/watch?v={}'.format(self.host, vid),
            'header': self.headers
        }