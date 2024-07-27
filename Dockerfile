# Stage 1: Build TensorFlow
FROM python:3.10.11 AS tensorflow-build

# Set the DEBIAN_FRONTEND to noninteractive to avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    lsb-release \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    unzip \
    patchelf && \
    rm -rf /var/lib/apt/lists/*

# Install additional Python dependencies
RUN pip install --no-cache-dir numpy==1.23.4 cython==0.29.36 wheel packaging requests

# Install Bazel 5.3.0
RUN curl -fsSL https://bazel.build/bazel-release.pub.gpg | gpg --dearmor >bazel-archive-keyring.gpg \
    && mv bazel-archive-keyring.gpg /usr/share/keyrings \
    && echo "deb [signed-by=/usr/share/keyrings/bazel-archive-keyring.gpg] https://storage.googleapis.com/bazel-apt stable jdk1.8" | tee /etc/apt/sources.list.d/bazel.list \
    && apt-get update && apt-get install -y bazel-5.3.0

# Ensure Bazel is in the PATH
RUN ln -s /usr/bin/bazel-5.3.0 /usr/bin/bazel

# Download and extract TensorFlow source code
RUN wget https://github.com/tensorflow/tensorflow/archive/refs/tags/v2.12.0.tar.gz -O tensorflow-2.12.0.tar.gz && \
    tar -xzf tensorflow-2.12.0.tar.gz && \
    mv tensorflow-2.12.0 /tensorflow && \
    rm tensorflow-2.12.0.tar.gz

# Configure TensorFlow build
WORKDIR /tensorflow

# Set custom CPU optimization flags
ENV CC_OPT_FLAGS="-march=core2 -mavx -msse4.1 -msse4.2 -mpclmul -mpopcnt -maes -mno-avx2"

# Export PATH to include Bazel
ENV PATH=/usr/local/bin:$PATH

# Use a heredoc to configure TensorFlow
RUN ./configure <<EOF
python
python
clang
clang
$CC_OPT_FLAGS
EOF

# Build TensorFlow with increased resources
RUN bazel build --jobs=12 --local_ram_resources=49152 --copt=-fPIC //tensorflow/tools/pip_package:build_pip_package

# Create the TensorFlow wheel
RUN ./bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg

# Stage 2: Install TensorFlow wheel and other dependencies
FROM python:3.10.11

# Set the DEBIAN_FRONTEND to noninteractive to avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y chromium chromium-driver xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/chromedriver /usr/local/bin/chromedriver

RUN apt-get update && apt-get install -y libhdf5-dev

# Copy the TensorFlow wheel from the first stage
COPY --from=tensorflow-build /tmp/tensorflow_pkg/tensorflow-2.12.0*.whl /tmp/

# Install the built TensorFlow package and other Python dependencies
RUN pip install --no-cache-dir /tmp/tensorflow-2.12.0*.whl \
    && pip uninstall -y jax jaxlib \
    && pip install --no-cache-dir \
        'git+https://github.com/exorde-labs/exorde_data.git' \
        'git+https://github.com/muhmad-f-k/exorde-client.git' \
        selenium==4.2.0 \
        wtpsplit==1.3.0 \
    && pip install --no-cache-dir --upgrade 'git+https://github.com/JustAnotherArchivist/snscrape.git'

# Clean cache now that we have installed everything
RUN rm -rf /root/.cache/* \
    && rm -rf /root/.local/cache/*

# Set display port to avoid crash
ENV DISPLAY=:99

COPY exorde/pre_install.py /exorde/exorde_install_models.py
WORKDIR /exorde

# Install all models: huggingface, langdetect, spacy
RUN mkdir -p /tmp/fasttext-langdetect
RUN wget -O /tmp/fasttext-langdetect/lid.176.bin https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
RUN python3.10 -m spacy download en_core_web_trf
RUN python3.10 exorde_install_models.py

# Install the app
COPY data /exorde

# Set the release version
ARG RELEASE_VERSION
RUN echo ${RELEASE_VERSION} > .release

# Set huggingface transformers cache
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV HF_HUB_OFFLINE=1

# Entry point is main.py
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
COPY keep_alive.sh /exorde/keep_alive.sh
RUN chmod +x /exorde/keep_alive.sh
RUN sed -i 's/\r$//' keep_alive.sh
ENTRYPOINT ["/bin/bash","/exorde/keep_alive.sh"]
