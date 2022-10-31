ARG SOURCE_DIR=/usr/src

FROM python:3.10-bullseye as build-stage

ARG SOURCE_DIR
ARG PATH="/root/.local/bin:${PATH}"

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry self add "poetry-dynamic-versioning[plugin]" \
    && poetry config virtualenvs.in-project true

WORKDIR ${SOURCE_DIR}
COPY . .
RUN rm -rf dist && poetry build --format wheel

FROM python:3.10-slim-bullseye as run-stage

ARG SOURCE_DIR

COPY --from=build-stage ${SOURCE_DIR}/dist/*.whl /tmp
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

CMD [ "python3", "-m", "bdp.homeassistant.speedtestwatchdog" ]
