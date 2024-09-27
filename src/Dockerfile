FROM pkgxdev/pkgx
# WORKDIR /app

# gets pkgx setup
# COPY .pkgx.yaml .
# RUN dev

# just install everything

RUN pkgx install python.org^3.11 astral.sh/uv^0 postgresql.org^16
COPY requirements.txt .
RUN CC=clang pkgx +clang@18 uv pip install -r requirements.txt --system
