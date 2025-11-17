import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    merge_dicts,
    orderedSet,
    unified_timestamp,
    url_or_none,
)


class EromeIE(InfoExtractor):
    IE_DESC = 'EroMe'
    _VALID_URL = r'https?://(?:www\.)?erome\.com/a/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://www.erome.com/a/JlMZFf4f',
        'info_dict': {
            'id': 'JlMZFf4f',
            'title': '🍒 Perfect Tits!!!!',
            'age_limit': 18,
            'description': 'md5:02591cd58c09a183e003b9a7a27ab79d',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://erome.com/a/TestAlbum123',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)
        display_id = album_id

        # Set age verification cookies before downloading
        self._set_cookie('erome.com', 'age_verified', '1')
        self._set_cookie('www.erome.com', 'age_verified', '1')

        webpage = self._download_webpage(url, album_id)

        # Check if content exists
        if any(x in webpage for x in [
            'This album no longer exists',
            'Album not found',
            'Album has been removed',
            'Page not found',
        ]):
            raise ExtractorError('Album not found', expected=True)

        # Try to extract JSON-LD structured data first
        json_ld = self._search_json_ld(webpage, album_id, default={})

        # Extract title with better patterns
        title = (json_ld.get('title') or self._html_search_regex(
            [r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>',
             r'<title>([^<]+)</title>'],
            webpage, 'title', default=None) or 'Untitled')

        # Clean title
        title = clean_html(title) or 'Untitled'
        if 'EroMe' in title:
            title = title.replace('EroMe - ', '').replace(' - EroMe', '').strip()
        if not title:
            title = 'Untitled'

        # Extract description if available
        description = (json_ld.get('description')
                       or self._og_search_description(webpage, default=None)
                       or self._html_search_regex(
            r'<meta name="description" content="([^"]+)"',
            webpage, 'description', fatal=False))

        # Extract uploader
        uploader = (json_ld.get('uploader')
                    or self._html_search_regex(
            r'<a[^>]+href="/[^"]+"[^>]*class="[^"]*username[^"]*"[^>]*>([^<]+)</a>',
            webpage, 'uploader', default=None))

        # Extract timestamp
        timestamp = (json_ld.get('timestamp')
                     or unified_timestamp(self._html_search_regex(
                         r'<span[^>]+class="[^"]*date[^"]*"[^>]*>([^<]+)</span>',
                         webpage, 'timestamp', default=None)))

        entries = []
        # Note: json_ld and display_id used in final return statement

        # Find video sources with multiple patterns
        video_patterns = [
            r'<source[^>]+src="([^"]+\.(?:mp4|webm|avi|mov|flv)(?:\?[^"]*)?)"[^>]*>',
            r'<video[^>]+src="([^"]+)"',
            r'"videoUrl":\s*"([^"]+)"',
        ]

        video_sources = []
        for pattern in video_patterns:
            matches = re.findall(pattern, webpage, re.IGNORECASE)
            video_sources.extend(matches)

        # Remove duplicates while preserving order
        video_sources = orderedSet(video_sources)

        for i, video_url in enumerate(video_sources):
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            elif video_url.startswith('/'):
                video_url = f'https://www.erome.com{video_url}'

            video_url = url_or_none(video_url)
            if video_url:
                entries.append({
                    'id': f'{album_id}_video_{i + 1}',
                    'url': video_url,
                    'title': f'{title} - Video {i + 1}',
                    'uploader': uploader,
                    'description': description,
                    'http_headers': {
                        'Referer': 'https://www.erome.com/',
                    },
                })

        # Extract images - look for content images in the album directory
        img_pattern = rf'''
            <img
                [^>]+
                src="
                (
                    https?://s\d+\.erome\.com/\d+/
                    {re.escape(album_id)}/
                    [^"]*\.                # filename and extension
                    (?:jpg|jpeg|png|gif)
                    (?:\?[^"]*)?           # optional query string
                )
                "
                [^>]*
            >
        '''
        img_matches = re.finditer(img_pattern, webpage, re.IGNORECASE | re.VERBOSE)

        img_urls = []
        for match in img_matches:
            img_url = match.group(1)
            if img_url:
                # Skip thumbnails and small images
                if not any(x in img_url for x in ['thumb', '_s.', '_t.', '/t/']):
                    img_url = url_or_none(img_url)
                    if img_url:
                        img_urls.append(img_url)

        # Remove duplicates while preserving order
        img_urls = orderedSet(img_urls)

        for i, img_url in enumerate(img_urls):
            entries.append({
                'id': f'{album_id}_img_{i + 1}',
                'url': img_url,
                'title': f'{title} - Image {i + 1}',
                'uploader': uploader,
                'ext': 'jpg',
                'description': description,
                'http_headers': {
                    'Referer': 'https://www.erome.com/',
                },
            })

        if not entries:
            raise ExtractorError('No media found', expected=True)

        # Use _rta_search for age limit detection (will return 18 for adult sites)
        age_limit = self._rta_search(webpage) or 18

        return merge_dicts(json_ld, {
            '_type': 'playlist',
            'id': album_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'entries': entries,
            'uploader': uploader,
            'timestamp': timestamp,
            'age_limit': age_limit,
        })


class EromeProfileIE(InfoExtractor):
    IE_DESC = 'EroMe user profile'
    _VALID_URL = r'https?://(?:www\.)?erome\.com/(?P<id>[a-zA-Z0-9_-]+)(?:\?page=\d+)?'
    _TESTS = [{
        'url': 'https://www.erome.com/username',
        'info_dict': {
            'id': 'username',
            'title': 'username - EroMe Profile',
            'age_limit': 18,
        },
        'playlist_mincount': 1,
        'skip': 'Profile test - requires valid profile URL',
    }]

    @classmethod
    def suitable(cls, url):
        return (False if EromeIE.suitable(url) else
                super().suitable(url))

    def _entries(self, profile_id):
        page_num = 1

        while True:
            # Set age verification cookies before downloading
            self._set_cookie('erome.com', 'age_verified', '1')
            self._set_cookie('www.erome.com', 'age_verified', '1')

            page_url = f'https://www.erome.com/{profile_id}' + ('' if page_num == 1 else f'?page={page_num}')
            webpage = self._download_webpage(
                page_url, profile_id,
                note=f'Downloading page {page_num}',
                fatal=False)

            if not webpage:
                break

            # Check if we've reached the end or hit an error page
            if any(x in webpage for x in [
                'User not found',
                'Profile not found',
                'This user does not exist',
                'Page not found',
            ]):
                break

            # Find album links on this page
            album_links = re.findall(
                r'href="(?:https?://(?:www\.)?erome\.com)?(/a/[a-zA-Z0-9]+)"',
                webpage)

            # Remove duplicates while preserving order
            album_links = orderedSet(album_links)

            if not album_links:
                break

            for album_path in album_links:
                album_url = f'https://www.erome.com{album_path}'
                album_id = album_path.split('/')[-1]
                yield self.url_result(
                    album_url, EromeIE.ie_key(),
                    video_id=album_id,
                    video_title=f'{profile_id} - Album {album_id}')

            # Check if there's a next page
            if f'/page/{page_num + 1}' not in webpage and f'page={page_num + 1}' not in webpage:
                break

            page_num += 1

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        profile_id = mobj.group('id')

        # Set age verification cookies before downloading
        self._set_cookie('erome.com', 'age_verified', '1')
        self._set_cookie('www.erome.com', 'age_verified', '1')

        # Download first page to get profile info
        webpage = self._download_webpage(
            f'https://www.erome.com/{profile_id}', profile_id)

        # Check if profile exists
        if any(x in webpage for x in [
            'User not found',
            'Profile not found',
            'This user does not exist',
            'Page not found',
        ]):
            raise ExtractorError('Profile not found', expected=True)

        # Try to extract JSON-LD structured data first
        json_ld = self._search_json_ld(webpage, profile_id, default={})

        # Extract profile title
        title = self._html_search_regex(
            [r'<h1[^>]*class="[^"]*username[^"]*"[^>]*>([^<]+)</h1>',
             r'<title>([^<]+)</title>'],
            webpage, 'title', default=f'{profile_id} - EroMe Profile')

        title = clean_html(title).strip()

        # Extract profile description if available
        description = (
            self._og_search_description(webpage, default=None)
            or self._html_search_regex(
                r'<meta name="description" content="([^"]+)"',
                webpage, 'description', fatal=False))

        # Use _rta_search for age limit detection
        age_limit = self._rta_search(webpage) or 18

        return merge_dicts(json_ld, {
            '_type': 'playlist',
            'id': profile_id,
            'title': title,
            'description': description,
            'entries': self._entries(profile_id),
            'age_limit': age_limit,
        })
