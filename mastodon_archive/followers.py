#!/usr/bin/env python3
# Copyright (C) 2018  Alex Schroeder <alex@gnu.org>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import os.path
from progress.bar import Bar
from datetime import timedelta, datetime
from . import core

def is_lurker(account, mentions):
    for mention in mentions:
        if account["id"] == mention["account"]["id"]:
            return False
    return True

def find_lurkers(followers, allowlist, mentions):
    return [x for x in followers
            if x["acct"] not in allowlist
            and is_lurker(x, mentions)]

def followers(args):
    """
    List followers
    """

    (username, domain) = args.user.split('@')

    status_file = domain + '.user.' + username + '.json'
    data = core.load(status_file, required=True, quiet=True, combine=True)

    # Print both error messages if the data is missing
    error = 0
    if args.mentions and "mentions" not in data or len(data["mentions"]) == 0:
        print("You need to run 'mastodon-archive archive --with-mentions'",
              file=sys.stderr)
        error = 5
    if "followers" not in data or len(data["followers"]) == 0:
        print("You need to run 'mastodon-archive archive --with-followers'",
              file=sys.stderr)
        error = 6
    if error > 0:
        sys.exit(error)

    # If we're not checking for mentions, this is quickly done.
    if not args.mentions:
        for account in sorted(data["followers"], key=lambda account:
                              account["display_name"] or account["username"]):
            print("%s <%s>" % (account["display_name"] or account["username"],
                               account["acct"]))
        sys.exit(0)

    if args.all:
        if not args.quiet:
            print("Considering the entire archive")
        mentions = data["mentions"]
    else:
        if not args.quiet:
            print("Considering the last "
                  + str(args.weeks)
                  + " weeks")
        mentions = core.keep(data["mentions"], args.weeks)

    allowlist = core.allowlist(domain, username)

    if args.block:
        mastodon = core.readwrite(args)
        accounts = find_lurkers(data["followers"], allowlist, mentions)

        if not args.quiet:
            bar = Bar('Blocking', max = len(accounts))

        for account in accounts:
            if not args.quiet:
                bar.next()
            try:
                mastodon.account_block(account["id"])
            except Exception as e:
                if "authorized scopes" in str(e):
                    print("\nWe need to authorize the app to make changes to your account.")
                    core.deauthorize(args)
                    mastodon = core.readwrite(args)
                    # retry
                    mastodon.account_block(account["id"])
                else:
                    print(e, file=sys.stderr)

        if not args.quiet:
            bar.finish()

    else:
        accounts = find_lurkers(data["followers"], allowlist, mentions)
        for account in sorted(accounts, key=lambda account:
                              account["display_name"] or account["username"]):
            print("%s <%s>" % (account["display_name"] or account["username"],
                               account["acct"]))
