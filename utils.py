import asyncio
from typing import List, Tuple

import requests

import config


async def get_meshy_job_id(prompt: str) -> str:
    try:
        payload = {
            "mode": "preview",
            "prompt": prompt,
            "art_style": "realistic",
            "negative_prompt": "low quality, low resolution, low poly, ugly"
        }
        headers = {
            "Authorization": f"Bearer {config.MESHY_API_KEY}"
        }
        response = requests.post(
            "https://api.meshy.ai/v2/text-to-3d",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        response = response.json()
        print(response)
        return response["result"]
    except:
        return ""


async def retriev_meshy_job_by_id(task_id: str) -> Tuple[List[str], bool]:
    headers = {
        "Authorization": f"Bearer {config.MESHY_API_KEY}"
    }
    flag = True
    status = False
    video_url = []
    while flag:
        response = requests.get(
            f"https://api.meshy.ai/v2/text-to-3d/{task_id}",
            headers=headers,
        )
        response.raise_for_status()
        if response.status_code == 200:
            response = response.json()
            print(response)
            if response["status"] == "SUCCEEDED":
                video_url.append(response["video_url"])
                flag = False
                status = True
            if response["status"] == "FAILED":
                flag = False
                status = True
        await asyncio.sleep(1)
    return video_url, status


async def call_meshy_api(prompt: str) -> Tuple[List[str], bool]:
    task_id = await get_meshy_job_id(prompt=prompt)
    if task_id == "":
        return [], False
    else:
        video_url, status = await retriev_meshy_job_by_id(task_id=task_id)
        return video_url, status
