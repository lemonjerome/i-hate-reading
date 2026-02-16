from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document

splitter = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=100
)

def chunk_document(text, source):
    doc=Document(
        text=text,
        metadata={"source": source}
    )

    nodes = splitter.get_nodes_from_documents([doc])
    return [{"text": node.txt, "chunk_index": i} for i in enumerate(nodes)]