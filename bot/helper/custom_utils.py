import re
import aiohttp
from time import time
from bot import LOGGER
from PIL import Image
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from bot.core.config_manager import Config
from os import path as ospath
from aiohttp import ClientSession as aioClientSession
from aiofiles import open as aiopen
from bot.helper.ext_utils.bot_utils import sync_to_async

async def download_image_url(url):
    path = "Images/"
    if not await aiopath.isdir(path):
        await mkdir(path)
    image_name = url.split('/')[-1]
    des_dir = ospath.join(path, image_name)
    async with aioClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiopen(des_dir, 'wb') as file:
                    async for chunk in response.content.iter_chunked(1024):
                        await file.write(chunk)
                LOGGER.info(f"Image Downloaded Successfully as {image_name}")
            else:
                LOGGER.error(f"Failed to Download Image from {url}")
    return des_dir

async def get_custom_thumb(self, thumb):
    photo_dir = await download_image_url(thumb)

    if await aiopath.exists(photo_dir):
        path = "Thumbnails"
        if not await aiopath.isdir(path):
            await mkdir(path)
        des_dir = ospath.join(path, f'{time()}.jpg')
        await sync_to_async(Image.open(photo_dir).convert("RGB").save, des_dir, "JPEG")
        await aioremove(photo_dir)
        return des_dir
    return None

async def extract_movie_info(caption):
    try:
        regex = re.compile(r'(.+?)(\d{4})')
        match = regex.search(caption)

        if match:
            # Replace '.' and remove '(' and ')' from movie_name
            movie_name = match.group(1).replace('.', ' ').replace('(', '').replace(')', '').strip()
            release_year = match.group(2)
            return movie_name, release_year
    except Exception as e:
        print(e)
    return None, None

async def get_by_name(movie_name, release_year):
    tmdb_search_url = f'https://api.themoviedb.org/3/search/multi?api_key={Config.TMDB_API_KEY}&query={movie_name}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tmdb_search_url) as search_response:
                search_data = await search_response.json()

                if search_data['results']:
                    matching_results = [
                        result for result in search_data['results']
                        if ('release_date' in result and result['release_date'][:4] == str(release_year)) or
                        ('first_air_date' in result and result['first_air_date'][:4] == str(release_year))
                    ]

                    if matching_results:
                        result = matching_results[0]
                        media_type = result['media_type']
                        movie_id = result['id']



                        tmdb_movie_image_url = f'https://api.themoviedb.org/3/{media_type}/{movie_id}/images?api_key={Config.TMDB_API_KEY}&language=en-US&include_image_language=en,hi'

                        async with session.get(tmdb_movie_image_url) as movie_response:
                            movie_images = await movie_response.json()
 

                        # Use the backdrop_path or poster_path
                            poster_path = None
                            if 'backdrops' in movie_images and movie_images['backdrops']:
                                poster_path = movie_images['backdrops'][0]['file_path']
                                                        
                            elif 'backdrop_path' in result and result['backdrop_path']:
                                poster_path = result['backdrop_path']
                            poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
                            return poster_url
    except Exception as e:
        print(f"Error fetching TMDB data: {e}")
    return None