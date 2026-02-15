from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=512,
    chucnk_overlap=100
)

def chunk_document(text):
    nodes = splitter.get_nodes_from_documents([text])
    return [node.text for node in nodes]