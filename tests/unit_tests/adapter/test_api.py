# pylint: disable=wrong-import-position
import os
from pathlib import Path

from gptcache.utils import import_ruamel
from gptcache.adapter.api import put, get, init_similar_cache, init_similar_cache_from_config
from gptcache.manager import CacheBase, VectorBase, get_data_manager
from gptcache.processor.pre import get_prompt
from gptcache.processor.post import nop
from gptcache import cache, Config, Cache
from gptcache.embedding import Onnx as EmbeddingOnnx
from gptcache.similarity_evaluation import SearchDistanceEvaluation

import_ruamel()

from ruamel.yaml import YAML


faiss_file = "faiss.index"


def test_gptcache_api():
    if os.path.isfile(faiss_file):
        os.remove(faiss_file)

    cache.init(pre_embedding_func=get_prompt)
    put("test_gptcache_api_hello", "foo")
    assert get("test_gptcache_api_hello") == "foo"

    inner_cache = Cache()
    init_similar_cache(
        data_dir="./",
        cache_obj=inner_cache,
        post_func=nop,
        config=Config(similarity_threshold=0),
    )

    put("api-hello1", "foo1", cache_obj=inner_cache)
    put("api-hello2", "foo2", cache_obj=inner_cache)
    put("api-hello3", "foo3", cache_obj=inner_cache)

    messages = get("hello", cache_obj=inner_cache, top_k=3)
    assert len(messages) == 3
    assert "foo1" in messages
    assert "foo2" in messages
    assert "foo3" in messages

    assert get("api-hello1") is None


def test_none_scale_data():
    if os.path.isfile(faiss_file):
        os.remove(faiss_file)

    def init_cache():
        embedding_onnx = EmbeddingOnnx()
        cache_base = CacheBase("sqlite")
        vector_base = VectorBase("faiss", dimension=embedding_onnx.dimension, top_k=10)
        data_manager = get_data_manager(cache_base, vector_base)

        evaluation = SearchDistanceEvaluation()
        inner_cache = Cache()
        inner_cache.init(
            pre_embedding_func=get_prompt,
            embedding_func=embedding_onnx.to_embeddings,
            data_manager=data_manager,
            similarity_evaluation=evaluation,
            post_process_messages_func=nop,
            config=Config(similarity_threshold=0),
        )
        return inner_cache

    inner_cache = init_cache()
    put("api-hello1", "foo1", cache_obj=inner_cache)

    os.remove("sqlite.db")
    inner_cache = init_cache()
    print("hello", get("api-hello1", cache_obj=inner_cache))
    assert get("api-hello1", cache_obj=inner_cache) is None


def test_init_with_config():
    yaml_path = Path("test.yaml")

    if yaml_path.exists():
        yaml_path.unlink()

    config = {
        "storage_config": {
            "manager": "sqlite,faiss",
            "data_dir": "./",
        },
        "model_source": "onnx",
        "evaluation": "distance",
        "pre_function": "get_prompt",
        "post_function": "first",
        "config_kws": {"threshold": 0}
    }

    with open(yaml_path, "w+", encoding="utf-8") as f:
        yaml = YAML(typ="unsafe", pure=True)
        yaml.dump(config, f)

    init_similar_cache_from_config(
        config_dir=yaml_path
    )

    put("api-hello", "foo")
    assert get("api-hello") == "foo"

    yaml_path.unlink()
