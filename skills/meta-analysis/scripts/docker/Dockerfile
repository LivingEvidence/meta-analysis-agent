FROM r-base:4.4.1

# Install system dependencies for R packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    cmake \
    libnlopt-dev \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Install R packages
RUN R -e "install.packages(c( \
    'meta', \
    'metafor', \
    'readxl', \
    'optparse', \
    'jsonlite', \
    'dplyr', \
    'rmarkdown' \
  ), repos='https://cloud.r-project.org/', Ncpus=4)"

WORKDIR /data
