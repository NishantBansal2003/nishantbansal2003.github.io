#!/usr/bin/env ruby
#
# Keep the day from each post's front matter `date:`, but take the time of
# day from the commit that first added the post (following renames).
# Posts not committed yet keep the time written in the front matter.

require 'time'

Jekyll::Hooks.register :site, :post_read do |site|
  site.posts.docs.each do |post|
    added = `git log --follow --diff-filter=A --format=%cI -- "#{post.path}"`.lines.last.to_s.strip
    next if added.empty?

    day = post.date
    time = Time.iso8601(added).getlocal(day.utc_offset)
    post.data['date'] = Time.new(day.year, day.month, day.day,
                                 time.hour, time.min, time.sec, day.utc_offset)
  end

  site.posts.docs.sort!
end
