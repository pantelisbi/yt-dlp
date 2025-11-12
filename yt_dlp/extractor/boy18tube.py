import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_to_int,
    unified_strdate,
)


class Boy18TubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?boy18tube\.com/video/(?P<id>\d+)/[^/]+\.php'
    _TESTS = [{
        'url': 'https://boy18tube.com/video/2534180/adult-time-cheating-nongay-guy-is-caught-assfucking-salute.php',
        'md5': 'todo',
        'info_dict': {
            'id': '2534180',
            'ext': 'mp4',
            'title': 'Adult Time: Cheating Nongay Guy Is Caught Assfucking Salute',
            'age_limit': 18,
        },
        'skip': 'Video may be removed or unavailable',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = (self._html_search_regex(
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

        # Extract metadata
        thumbnail = (self._og_search_thumbnail(webpage, default=None)
                     or self._html_search_meta('twitter:image', webpage, 'thumbnail', default=None))

        description = (self._og_search_description(webpage, default=None)
                       or self._html_search_meta('description', webpage, 'description', default=None))

        # Extract uploader
        uploader = self._html_search_regex(
            r'<i[^>]*class="icon-user-male"[^>]*></i>\s*Uploaded\s+by:\s*</span>\s*(?:<span>)?\s*([^<]+)',
            webpage, 'uploader', default=None, fatal=False)

        # Extract upload date
        upload_date = self._html_search_regex(
            r'<i\s+class="icon-calendar"></i>Added\s+on:</span>\s*<span>([^<]+)</span>',
            webpage, 'upload date', default=None)
        if upload_date:
            upload_date = unified_strdate(upload_date)

        # Extract view count
        view_count = self._html_search_regex(
            r'<i\s+class="icon-star"></i>Views:</span>\s*(\d+)',
            webpage, 'view count', default=None)
        if view_count:
            view_count = str_to_int(view_count)

        # Duration is not reliably available on the page (only shows on thumbnails)
        # yt-dlp will automatically extract it from the video file during download
        duration = None

        # Extract categories
        categories = self._html_search_regex(
            r'<i\s+class="icon-list"></i>Categories:</span>(.*?)</div>',
            webpage, 'categories', default='', flags=0)
        categories = [cat.strip() for cat in self._html_search_regex(
            r'<a[^>]+>([^<]+)</a>', categories, 'category', default='').split(',') if cat.strip()]

        # Extract tags
        tags_section = self._html_search_regex(
            r'<i\s+class="icon-tags"></i>Tags:</span>(.*?)</div>',
            webpage, 'tags section', default='', flags=0)
        tags = [tag.strip() for tag in re.findall(r'<a[^>]+>([^<]+)</a>', tags_section or '') if tag.strip()]

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'description': description,
            'uploader': uploader,
            'upload_date': upload_date,
            'view_count': view_count,
            'duration': duration,
            'categories': categories if categories else None,
            'tags': tags if tags else None,
            'age_limit': 18,
            'http_headers': {
                'Referer': 'https://boy18tube.com/',
            },
        }
