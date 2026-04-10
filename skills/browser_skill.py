# 1. stdlib
import logging
import webbrowser
import urllib.parse

# 2. internal
# No internal imports needed yet

logger = logging.getLogger('dna.skill.browser')


def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    try:
        # Ensure url has a scheme
        preserved_url = url.strip()
        scheme_check = preserved_url.lower()
        if not (scheme_check.startswith('http://') or scheme_check.startswith('https://')):
            preserved_url = 'https://' + preserved_url
            
        webbrowser.open(preserved_url)
        return 'Sure, opening that website for you.'
    except Exception as e:
        logger.error('open_url failed: %s', e)
        return f'Could not open the website: {str(e)}'


def search_google(query: str) -> str:
    """Search Google for a query."""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f'https://www.google.com/search?q={encoded_query}'
        webbrowser.open(url)
        return 'Searching Google for you now.'
    except Exception as e:
        logger.error('search_google failed: %s', e)
        return f'Could not search Google: {str(e)}'


def search_youtube(query: str) -> str:
    """Search YouTube for a query."""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f'https://www.youtube.com/results?search_query={encoded_query}'
        webbrowser.open(url)
        return 'Alright, looking that up on YouTube.'
    except Exception as e:
        logger.error('search_youtube failed: %s', e)
        return f'Could not search YouTube: {str(e)}'


# Skill module contract
TOOLS = {
    'open_url': open_url,
    'search_google': search_google,
    'search_youtube': search_youtube,
}
