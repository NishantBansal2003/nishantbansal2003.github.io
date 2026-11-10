#!/usr/bin/env ruby
#
# Show the affected/fixed summary box at the top of any post whose
# front matter has a `disclosure:` block (see _includes/disclosure.html).

Jekyll::Hooks.register :posts, :pre_render do |post|
  next unless post.data['disclosure']

  post.content = "{% include disclosure.html %}\n\n" + post.content
end
