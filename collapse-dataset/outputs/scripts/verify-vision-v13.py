"""End-to-end verification of dsh-vision v1.3: status, smart PDF routing, OCR, VLM."""
import asyncio
import json
import os

PDF = r"E:\Deepseek\reference_file\CH634DS1.PDF"
PAGE1 = r"D:\AI_file\workspace\pdf-pages\page01.png"
OUT = r"E:\Deepseek\workspace\conv-20260928-3b54e160\mcp-v13-verification.txt"

CALLS = [
    ("vision_status", {}),
    ("vision_read_document", {"path": PDF, "pages": "2-3", "dpi": 150}),
    ("vision_read_document", {"path": PDF, "pages": "2", "prefer": "vlm"}),
    ("vision_ask", {"image_path": PAGE1, "question": "What chip is this datasheet about, and what are its main features?"}),
]


async def main() -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=r"D:\AI_file\envs\openvino\Scripts\python.exe",
        args=[r"D:\AI_file\mcp\vision-server.py"],
        env={**os.environ, "DSH_VISION_DEVICE": "NPU"},
        cwd=r"D:\AI_file\mcp",
    )
    blocks = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools: " + ", ".join(t.name for t in tools.tools))
            blocks.append("tools: " + ", ".join(t.name for t in tools.tools))
            for tool, args in CALLS:
                print("\n### %s %s" % (tool, json.dumps(args, ensure_ascii=False)))
                res = await session.call_tool(tool, args)
                text = "\n".join(str(getattr(b, "text", b)) for b in res.content)
                print(text[:1500])
                blocks.append("### %s %s\n%s" % (tool, json.dumps(args, ensure_ascii=False), text))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(blocks))
    print("\nwritten: " + OUT)


asyncio.run(main())