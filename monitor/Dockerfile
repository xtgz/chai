FROM pkgxdev/pkgx:latest
RUN pkgx install python.org^3.11 astral.sh/uv^0
COPY requirements.txt .
RUN CC=clang pkgx +clang@18 uv pip install -r requirements.txt --system