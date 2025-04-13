class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size=1000, chunk_overlap=200, separators=None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text):
        def split_with_separator(text, separator):  # noqa: ANN202
            return text.split(separator) if separator else [text]

        for separator in self.separators:
            if len(text) <= self.chunk_size:
                return [text]
            chunks = []
            splits = split_with_separator(text, separator)
            current_chunk = ""
            for split in splits:
                if len(current_chunk) + len(split) + 1 > self.chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = split
                else:
                    current_chunk += (separator if current_chunk else "") + split
            if current_chunk:
                chunks.append(current_chunk.strip())
            if all(len(chunk) <= self.chunk_size for chunk in chunks):
                return chunks
        return [text]
