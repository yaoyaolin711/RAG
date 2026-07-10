import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import TOP_K
from vectorstore import get_vector_store, check_milvus_connection


class TestVectorStore:
    @pytest.fixture(autouse=True)
    def setup(self):
        check_milvus_connection()
        self.vector_store = get_vector_store()

    def test_similarity_search(self):
        query = "锦丞商城满多少免运费？"
        retrieved_docs = self.vector_store.similarity_search(query, k=TOP_K)

        assert len(retrieved_docs) > 0

        for doc in retrieved_docs:
            print("---" * 10)
            print(doc.metadata.get("source", "未知"))
            print(doc.page_content)
            print("---" * 10)
