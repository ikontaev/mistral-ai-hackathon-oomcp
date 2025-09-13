def register(mcp):
    @mcp.tool
    def generate_html(title: str, body: str, name: str) -> str:
        """Generate a simple HTML file based on title and body content inside a template and it writes to filesystem with
        params:
        title: str
        body: str
        name: str (without .html extension)
        """
        try:
            html_content = f"""<!DOCTYPE html>
    <html lang="en"> 
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body>
        {body}
    </body>
    </html>"""
            with open(f"{name}.html", "w") as f:
                f.write(html_content)
            return f"{name}.html"
        except Exception as e:
            return f"❌ Error generating HTML: {str(e)}"
    