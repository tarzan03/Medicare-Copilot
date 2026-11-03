# import re

# kk = ">=45"

# num = re.findall(r"-?\d+\.?\d*", kk)
# print(type(int(num[0])))

import cohere
from src.medicare_copilot.utils.settings import settings

text = [
    "Dogs are loyal",
    "camels are tall",
    "giraffs are taller than elephants",
    "tesla roadster can fly now",
]
co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

response = co.embed(
    model="embed-v4.0", input_type="classification", output_dimension=1024
)

embeddings = response.embed(text)
