import functools
import time
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    int_or_none,
    qualities,
    try_get,
)


class RedGifsBaseIE(InfoExtractor):
    _FORMATS = {
        'gif': 250,
        'sd': 480,
        'hd': None,
    }

    _API_HEADERS = {
        'referer': 'https://www.redgifs.com/',
        'origin': 'https://www.redgifs.com',
        'content-type': 'application/json',
    }

    def _parse_gif_data(self, gif_data):
        video_id = gif_data.get('id')
        quality = qualities(tuple(self._FORMATS.keys()))

        orig_height = int_or_none(gif_data.get('height'))
        aspect_ratio = try_get(gif_data, lambda x: orig_height / x['width'])

        formats = []
        for format_id, height in self._FORMATS.items():
            video_url = gif_data['urls'].get(format_id)
            if not video_url:
                continue
            height = min(orig_height, height or orig_height)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'width': height * aspect_ratio if aspect_ratio else None,
                'height': height,
                'quality': quality(format_id),
            })

        return {
            'id': video_id,
            'webpage_url': f'https://redgifs.com/watch/{video_id}',
            'extractor_key': RedGifsIE.ie_key(),
            'extractor': 'RedGifs',
            'title': ' '.join(gif_data.get('tags') or []) or 'RedGifs',
            'timestamp': int_or_none(gif_data.get('createDate')),
            'uploader': gif_data.get('userName'),
            'duration': int_or_none(gif_data.get('duration')),
            'view_count': int_or_none(gif_data.get('views')),
            'like_count': int_or_none(gif_data.get('likes')),
            'categories': gif_data.get('tags') or [],
            'tags': gif_data.get('tags'),
            'age_limit': 18,
            'formats': formats,
        }

    def _fetch_oauth_token(self, video_id):
        # https://github.com/Redgifs/api/wiki/Temporary-tokens
        auth = self._download_json('https://api.redgifs.com/v2/auth/temporary',
                                   video_id, note='Fetching temporary token')
        if not auth.get('token'):
            raise ExtractorError('Unable to get temporary token')
        self._API_HEADERS['authorization'] = f'Bearer {auth["token"]}'

    def _call_api(self, ep, video_id, **kwargs):
        for retry in self.RetryManager():
            try:
                # Refresh token if needed or on 401
                for first_attempt in True, False:
                    if 'authorization' not in self._API_HEADERS:
                        self._fetch_oauth_token(video_id)
                    try:
                        headers = dict(self._API_HEADERS)
                        headers['x-customheader'] = f'https://www.redgifs.com/watch/{video_id}'
                        data = self._download_json(
                            f'https://api.redgifs.com/v2/{ep}', video_id, headers=headers, **kwargs)
                        break
                    except ExtractorError as e:
                        if first_attempt and isinstance(e.cause, HTTPError) and e.cause.status == 401:
                            del self._API_HEADERS['authorization']  # refresh the token
                            continue
                        raise
                if 'error' in data:
                    raise ExtractorError(f'RedGifs said: {data["error"]}', expected=True, video_id=video_id)
                return data
            except ExtractorError as e:
                # Handle 429 Too Many Requests with retry
                if isinstance(e.cause, HTTPError) and e.cause.status == 429:
                    self.report_warning(
                        'Rate limit reached. Retrying with exponential backoff...', only_once=True)
                    retry.error = e.cause
                    continue
                raise

    def _fetch_page(self, ep, video_id, query, page):
        query['page'] = page + 1
        # Add a small delay between paginated requests to avoid rate limiting
        if page > 0:
            sleep_interval = self.get_param('sleep_interval_requests') or 0.5
            if sleep_interval > 0:
                time.sleep(sleep_interval)
        data = self._call_api(
            ep, video_id, query=query, note=f'Downloading JSON metadata page {page + 1}')

        for entry in data['gifs']:
            yield self._parse_gif_data(entry)

    def _prepare_api_query(self, query, fields):
        api_query = [
            (field_name, query.get(field_name, (default,))[0])
            for field_name, default in fields.items()]

        return {key: val for key, val in api_query if val is not None}

    def _paged_entries(self, ep, item_id, query, fields):
        page = int_or_none(query.get('page', (None,))[0])
        page_fetcher = functools.partial(
            self._fetch_page, ep, item_id, self._prepare_api_query(query, fields))
        return page_fetcher(page) if page else OnDemandPagedList(page_fetcher, self._PAGE_SIZE)


class RedGifsIE(RedGifsBaseIE):
    _VALID_URL = r'https?://(?:(?:www\.)?redgifs\.com/(?:watch|ifr)/|thumbs2\.redgifs\.com/)(?P<id>[^-/?#\.]+)'
    _TESTS = [{
        'url': 'https://www.redgifs.com/watch/squeakyhelplesswisent',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
            'tags': list,
        },
    }, {
        'url': 'https://thumbs2.redgifs.com/SqueakyHelplessWisent-mobile.mp4#t=0',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
            'tags': list,
        },
    }, {
        'url': 'https://www.redgifs.com/ifr/squeakyhelplesswisent',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
            'tags': list,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).lower()
        video_info = self._call_api(
            f'gifs/{video_id}?views=yes', video_id, note='Downloading video info')
        return self._parse_gif_data(video_info['gif'])


class RedGifsSearchIE(RedGifsBaseIE):
    IE_DESC = 'Redgifs search'
    _VALID_URL = r'https?://(?:www\.)?redgifs\.com/browse\?(?P<query>[^#]+)'
    _PAGE_SIZE = 80
    _TESTS = [
        {
            'url': 'https://www.redgifs.com/browse?tags=Lesbian',
            'info_dict': {
                'id': 'tags=Lesbian',
                'title': 'Lesbian',
                'description': 'RedGifs search for Lesbian, ordered by trending',
            },
            'playlist_mincount': 100,
        },
        {
            'url': 'https://www.redgifs.com/browse?type=g&order=latest&tags=Lesbian',
            'info_dict': {
                'id': 'type=g&order=latest&tags=Lesbian',
                'title': 'Lesbian',
                'description': 'RedGifs search for Lesbian, ordered by latest',
            },
            'playlist_mincount': 100,
        },
        {
            'url': 'https://www.redgifs.com/browse?type=g&order=latest&tags=Lesbian&page=2',
            'info_dict': {
                'id': 'type=g&order=latest&tags=Lesbian&page=2',
                'title': 'Lesbian',
                'description': 'RedGifs search for Lesbian, ordered by latest',
            },
            'playlist_count': 80,
        },
    ]

    def _real_extract(self, url):
        query_str = self._match_valid_url(url).group('query')
        query = urllib.parse.parse_qs(query_str)
        if not query.get('tags'):
            raise ExtractorError('Invalid query tags', expected=True)

        tags = query.get('tags')[0]
        order = query.get('order', ('trending',))[0]

        query['search_text'] = [tags]
        entries = self._paged_entries('gifs/search', query_str, query, {
            'search_text': None,
            'order': 'trending',
            'type': None,
        })

        return self.playlist_result(
            entries, query_str, tags, f'RedGifs search for {tags}, ordered by {order}')


class RedGifsUserIE(RedGifsBaseIE):
    IE_DESC = 'Redgifs user'
    _VALID_URL = r'https?://(?:www\.)?redgifs\.com/users/(?P<username>[^/?#]+)(?:\?(?P<query>[^#]+))?'
    _PAGE_SIZE = 80
    _TESTS = [
        {
            'url': 'https://www.redgifs.com/users/lamsinka89',
            'info_dict': {
                'id': 'lamsinka89',
                'title': 'lamsinka89',
                'description': 'RedGifs user lamsinka89, ordered by recent',
            },
            'playlist_mincount': 391,
        },
        {
            'url': 'https://www.redgifs.com/users/lamsinka89?page=3',
            'info_dict': {
                'id': 'lamsinka89?page=3',
                'title': 'lamsinka89',
                'description': 'RedGifs user lamsinka89, ordered by recent',
            },
            'playlist_count': 80,
        },
        {
            'url': 'https://www.redgifs.com/users/lamsinka89?order=best&type=g',
            'info_dict': {
                'id': 'lamsinka89?order=best&type=g',
                'title': 'lamsinka89',
                'description': 'RedGifs user lamsinka89, ordered by best',
            },
            'playlist_mincount': 391,
        },
        {
            'url': 'https://www.redgifs.com/users/ignored52',
            'note': 'https://github.com/yt-dlp/yt-dlp/issues/7382',
            'info_dict': {
                'id': 'ignored52',
                'title': 'ignored52',
                'description': 'RedGifs user ignored52, ordered by recent',
            },
            'playlist_mincount': 121,
        },
    ]

    def _real_extract(self, url):
        username, query_str = self._match_valid_url(url).group('username', 'query')
        playlist_id = f'{username}?{query_str}' if query_str else username

        query = urllib.parse.parse_qs(query_str)
        order = query.get('order', ('recent',))[0]

        entries = self._paged_entries(f'users/{username}/search', playlist_id, query, {
            'order': 'recent',
            'type': None,
        })

        return self.playlist_result(
            entries, playlist_id, username, f'RedGifs user {username}, ordered by {order}')


class RedGifsNicheIE(RedGifsBaseIE):
    IE_DESC = 'Redgifs niche'
    _VALID_URL = r'https?://(?:www\.)?redgifs\.com/niches/(?P<slug>[^/?#]+)(?:\?(?P<query>[^#]+))?'
    _PAGE_SIZE = 100
    _TESTS = [{
        'url': 'https://www.redgifs.com/niches/hot-guys',
        'info_dict': {
            'id': 'hot-guys',
            'title': 'Hot Guys',
            'description': 'RedGifs niche Hot Guys, ordered by recent',
        },
        'playlist_mincount': 100,
    }]

    def _real_extract(self, url):
        slug, query_str = self._match_valid_url(url).group('slug', 'query')
        playlist_id = f'{slug}?{query_str}' if query_str else slug

        query = urllib.parse.parse_qs(query_str) if query_str else {}
        order = query.get('order', ('recent',))[0]
        requested_page = int_or_none(query.get('page', (None,))[0])
        api_query = self._prepare_api_query(query, {
            'order': 'recent',
            'type': None,
            'sexuality': None,
        })

        niche_info = self._call_api(f'niches/{slug}', slug, note='Downloading niche metadata').get('niche') or {}
        entries = (
            self._niche_page_entries(slug, playlist_id, api_query, requested_page)
            if requested_page else self._niche_entries(slug, playlist_id, api_query))

        title = niche_info.get('name') or slug
        description = niche_info.get('description')
        return self.playlist_result(
            entries, playlist_id, title, f'RedGifs niche {title}, ordered by {order}',
            description=description)

    def _niche_page_entries(self, slug, playlist_id, api_query, page):
        data = self._download_niche_page(slug, playlist_id, api_query, (page or 0))
        for gif in data.get('gifs') or []:
            yield self._parse_gif_data(gif)

    def _niche_entries(self, slug, playlist_id, api_query):
        page = 0
        total_pages = None
        while True:
            data = self._download_niche_page(slug, playlist_id, api_query, page)
            gifs = data.get('gifs') or []
            for gif in gifs:
                yield self._parse_gif_data(gif)
            if not gifs:
                break
            total_pages = total_pages or int_or_none(data.get('pages'))
            if total_pages and page + 1 >= total_pages:
                break
            page += 1

    def _download_niche_page(self, slug, playlist_id, api_query, page):
        query = dict(api_query)
        query['page'] = page + 1
        # Add a small delay between paginated requests to avoid rate limiting
        if page > 0:
            sleep_interval = self.get_param('sleep_interval_requests') or 0.5
            if sleep_interval > 0:
                time.sleep(sleep_interval)
        return self._call_api(
            f'niches/{slug}/gifs', playlist_id, query=query,
            note=f'Downloading JSON metadata page {page + 1}')
