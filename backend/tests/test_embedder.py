"""Tests the real BAAI/bge-large-en-v1.5 embedding model (app/rag/embedder.py).

Marked slow: downloads a ~1.3GB model on first run on a machine that hasn't
cached it yet, and loading/running it takes real time even when cached --
run explicitly with `pytest -m slow`, not part of the default fast suite."""
import numpy as np
import pytest

from app.rag.embedder import embed_passages, embed_query

pytestmark = pytest.mark.slow


def test_embed_passages_returns_correct_shape_and_is_normalized():
    embeddings = embed_passages(["Client shall pay invoices within fifteen days of receipt.", "Provider shall migrate workloads to the cloud."])
    assert embeddings.shape == (2, 1024)
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-4)


def test_embed_passages_handles_empty_list():
    embeddings = embed_passages([])
    assert embeddings.shape == (0, 1024)


def test_embed_query_returns_correct_shape_and_is_normalized():
    embedding = embed_query("What are the payment terms?")
    assert embedding.shape == (1024,)
    assert abs(np.linalg.norm(embedding) - 1.0) < 1e-4


def test_semantically_similar_passages_are_closer_than_unrelated_ones():
    """Sanity check that this is actually doing semantic embedding, not just
    producing arbitrary vectors -- a payment-related query should be closer
    to a payment clause than to an unrelated migration clause."""
    passages = embed_passages(
        [
            "Client shall pay all undisputed invoices within forty-five days of receipt.",
            "Provider will migrate Client's on-premises workloads to a cloud environment.",
        ]
    )
    query = embed_query("When is payment due?")
    similarity_to_payment_clause = float(np.dot(query, passages[0]))
    similarity_to_migration_clause = float(np.dot(query, passages[1]))
    assert similarity_to_payment_clause > similarity_to_migration_clause
