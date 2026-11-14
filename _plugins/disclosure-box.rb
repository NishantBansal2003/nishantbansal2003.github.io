#!/usr/bin/env ruby
#
# Show the affected/fixed summary box at the top of any post whose
# front matter has a `disclosure:` block (see _includes/disclosure.html).
#
# A post with `republished_from: <url>` also gets a note crediting the
# original source, placed above the disclosure box.

require 'uri'

Jekyll::Hooks.register :posts, :pre_render do |post|
  header = ''

  if (url = post.data['republished_from'])
    host = URI(url).host.to_s.sub(/\Awww\./, '')
    header += "> This advisory was originally published at [#{host}](#{url}) " \
              "and is reproduced here for my personal security research archive.\n" \
              "{: .prompt-info }\n\n"
  end

  header += "{% include disclosure.html %}\n\n" if post.data['disclosure']

  post.content = header + post.content unless header.empty?
end
