import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    merge_dicts,
    parse_duration,
    str_to_int,
    unified_strdate,
    unified_timestamp,
)


class Boy18TubeIE(InfoExtractor):
    IE_DESC = 'Boy18Tube'
    _VALID_URL = r'https?://(?:www\.)?boy18tube\.com/video/(?P<id>\d+)/(?P<display_id>[^/]+)\.php'
    _TESTS = [{
        'url': 'https://boy18tube.com/video/2534180/adult-time-cheating-nongay-guy-is-caught-assfucking-salute.php',
        'info_dict': {
            'id': '2534180',
            'display_id': 'adult-time-cheating-nongay-guy-is-caught-assfucking-salute',
            'ext': 'mp4',
            'title': 'Adult Time: Cheating Nongay Guy Is Caught Assfucking Salute',
            'age_limit': 18,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Video may be removed or unavailable',
    }, {
        'url': 'https://www.boy18tube.com/video/1234567/test-video.php',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, video_id)

        # Try to extract JSON-LD structured data first for better metadata
        json_ld = self._search_json_ld(webpage, video_id, default={})

        # Extract title with multiple fallback methods
        title = (json_ld.get('title')
                 or self._html_search_regex(
            r'<title>([^<]+)</title>', webpage, 'title', default=None)
            or self._og_search_title(webpage, default=None)
            or self._html_search_meta('twitter:title', webpage, 'title', default=None))

        if title:
            # Clean up title by removing site name and suffixes
            title = re.sub(r'\s*(?:-|at)\s*Boy\s*18\s*Tube\s*$', '', title, flags=re.IGNORECASE).strip()

        # Try to extract video from dynamically loaded player
        formats = []

        # Method 1: Try the video update URL endpoint
        video_update_url = self._search_regex(
            r'data-v-update-url="([^"]+)"', webpage, 'video update url', default=None)

        if video_update_url:
            # Append video ID to get actual video URL
            if not video_update_url.endswith('/'):
                video_update_url += '/'
            video_url_api = f'{video_update_url}{video_id}'

            # Download video info JSON (silently fall back if not available)
            video_data = self._download_json(
                video_url_api, video_id, note=False, errnote=False, fatal=False)

            if isinstance(video_data, dict):
                # Extract video sources
                if 'sources' in video_data:
                    for source in video_data['sources']:
                        if isinstance(source, dict) and 'src' in source:
                            formats.append({
                                'url': source['src'],
                                'format_id': source.get('label', source.get('quality', 'default')),
                                'height': int_or_none(source.get('quality')),
                            })
                elif 'url' in video_data:
                    formats.append({'url': video_data['url']})
                elif 'file' in video_data:
                    formats.append({'url': video_data['file']})

        # Method 2: Try to extract video directly from webpage
        if not formats:
            for pattern in [
                r'<source[^>]+src="([^"]+\.mp4[^"]*)"',
                r'<video[^>]+src="([^"]+\.mp4[^"]*)"',
                r'"file"\s*:\s*"([^"]+\.mp4[^"]*)"',
                r'"url"\s*:\s*"([^"]+\.mp4[^"]*)"',
                r'(?:file|src|url)\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            ]:
                video_src = self._search_regex(pattern, webpage, 'video source', default=None)
                if video_src:
                    formats.append({'url': video_src})
                    break

        if not formats:
            raise ExtractorError('Unable to extract video URL', expected=True)

        # Extract metadata with fallbacks from JSON-LD
        thumbnail = (json_ld.get('thumbnail')
                     or self._og_search_thumbnail(webpage, default=None)
                     or self._html_search_meta('twitter:image', webpage, 'thumbnail', default=None))

        description = (json_ld.get('description')
                       or self._og_search_description(webpage, default=None)
                       or self._html_search_meta('description', webpage, 'description', default=None))

        # Extract uploader
        uploader = (json_ld.get('uploader')
                    or self._html_search_regex(
            r'<i[^>]*class="icon-user-male"[^>]*></i>\s*Uploaded\s+by:\s*</span>\s*(?:<span>)?\s*([^<]+)',
            webpage, 'uploader', default=None, fatal=False))

        # Extract timestamp and upload date
        timestamp = json_ld.get('timestamp')
        upload_date = None
        if not timestamp:
            upload_date_str = self._html_search_regex(
                r'<i\s+class="icon-calendar"></i>Added\s+on:</span>\s*<span>([^<]+)</span>',
                webpage, 'upload date', default=None)
            if upload_date_str:
                timestamp = unified_timestamp(upload_date_str)
                upload_date = unified_strdate(upload_date_str)

        # Extract view count
        view_count = (json_ld.get('view_count')
                      or str_to_int(self._html_search_regex(
                          r'<i\s+class="icon-star"></i>Views:</span>\s*([\d,]+)',
                          webpage, 'view count', default=None)))

        # Extract duration
        duration = (json_ld.get('duration')
                    or parse_duration(self._html_search_regex(
                        r'<i\s+class="icon-clock"></i>Duration:</span>\s*([^<]+)',
                        webpage, 'duration', default=None))
                    or int_or_none(self._html_search_meta('duration', webpage, default=None)))

        # Extract categories
        categories = json_ld.get('categories')
        if not categories:
            categories_html = self._html_search_regex(
                r'<i\s+class="icon-list"></i>Categories:</span>(.*?)</div>',
                webpage, 'categories', default='', flags=re.DOTALL)
            categories = [clean_html(cat).strip() for cat in re.findall(
                r'<a[^>]+>([^<]+)</a>', categories_html) if clean_html(cat).strip()] or None

        # Extract tags
        tags = json_ld.get('tags')
        if not tags:
            tags_html = self._html_search_regex(
                r'<i\s+class="icon-tags"></i>Tags:</span>(.*?)</div>',
                webpage, 'tags section', default='', flags=re.DOTALL)
            tags = [clean_html(tag).strip() for tag in re.findall(
                r'<a[^>]+>([^<]+)</a>', tags_html) if clean_html(tag).strip()] or None

        # Extract like/dislike counts if available
        like_count = str_to_int(self._html_search_regex(
            r'<i\s+class="icon-thumbs-up"></i>\s*([\d,]+)',
            webpage, 'like count', default=None))

        dislike_count = str_to_int(self._html_search_regex(
            r'<i\s+class="icon-thumbs-down"></i>\s*([\d,]+)',
            webpage, 'dislike count', default=None))

        # Use _rta_search for age limit detection
        age_limit = self._rta_search(webpage) or 18

        # Merge JSON-LD data with extracted data using merge_dicts
        return merge_dicts(json_ld, {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'description': description,
            'uploader': uploader,
            'timestamp': timestamp,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'categories': categories,
            'tags': tags,
            'age_limit': age_limit,
            'http_headers': {
                'Referer': 'https://boy18tube.com/',
            },
        })
