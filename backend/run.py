"""Khởi động FastAPI server."""

import uvicorn

from app.config import HOST, PORT, RELOAD


def main() -> None:
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)


if __name__ == "__main__":
    main()
