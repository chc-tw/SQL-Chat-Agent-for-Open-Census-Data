import frontmatter

def process_markdown_file(file_path: str) -> tuple[dict, str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    metadata = post.metadata
    content = post.content

    return metadata, content