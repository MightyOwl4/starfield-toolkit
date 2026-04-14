# Jekyll preview image matching GitHub Pages' Ruby version.
# https://pages.github.com/versions/
FROM ruby:3.3-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /site

# Install gems first so bundle is cached across source edits.
COPY Gemfile ./
RUN bundle install

EXPOSE 4000 35729

# Defaults are overridden by docker-compose command.
CMD ["bundle", "exec", "jekyll", "serve", \
     "--host", "0.0.0.0", \
     "--livereload", \
     "--force_polling", \
     "--baseurl", ""]
