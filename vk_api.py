# Позволяет получать информацию о пользователе, сообществах, записях на стене

import time
import requests
import uuid
import re

"""
Algorithm for registering your VK-application (for working with the API):
    1. Go to: https://vk.com/apps?act=manage
    2. Click the "Create" button
    3. Write any name of app
    4. Platform - Embedded application
    5. You can specify any category
    6. Click "Go to settings" button
    7. Confirm
    8. Copy the application ID
"""
VK_API_URL = 'https://api.vk.com/method/'
VK_OAUTH_URL = 'https://oauth.vk.com/'
VK_API_VERSION = '5.199'
VK_API_RPS_LIMIT = 5  # limit of requests per seconds
# Authentication Option 1:
#   1. Insert an access token in VK_API_TOKEN (example: vk1.a.abcde... [198 symbols])
VK_API_TOKEN = ''  # INSERT_YOUR_API_TOKEN_from_generated_OAUTH_URL
VK_API_RESERVE_TOKENS = []  # additional reserve API tokens
# Authentication Option 2:
#   1. Leave VK_API_TOKEN empty, insert VK_APP_SCOPE, VK_APP_ID (or don't change them to get full permissions)
#   2. Follow the instructions when executing script to obtain token
VK_APP_ID = ''  # INSERT_YOUR_APP_ID_from_VK_ACCOUNT
VK_APP_SCOPE = 'friends,groups'
               #'ads,audio,docs,email,friends,groups,market,menu,messages,notes,notifications,notify,pages,' \
               #'phone_number,photos,stats,status,stories,video,wall,' \
               #'offline'  # These all possible scopes. You can choose only you need. offline - for non expires token


class VK:
    """VK API for users, groups, wall info"""
    # screen_name input formats = ([int] 1234567, [str] '1234567', [str] 'id1234567', [str] '1234567_screen_name')

    def __init__(
            self,
            api_url: str = '',  # VK API
            oauth_url: str = '',  # VK authentication
            app_id: str | int = '',  # VK App ID
            app_scope: str = '',  # VK App scope
            api_token: str = '',  # VK API token
            api_tokens_reserve: list = [],  # VK API reserve tokens
            api_version: str = '',  # VK API version
            api_rps_limit: int = 5,  # VK API limit of requests per second
    ) -> None:
        self._api_ulr = api_url
        self._oauth_url = oauth_url
        self._app_id = app_id
        self._app_scope = app_scope
        self._api_version = api_version
        self._uuid = str(uuid.uuid4())
        self._api_rps_limit = 1 / api_rps_limit
        self._time_last_request = 0.0
        self._api_tokens_reserve = api_tokens_reserve
        if api_token:
            self._api_token = api_token
        elif not self._get_reserve_token():
            self._api_token = self._get_access_token_by_url()

    def _get_reserve_token(self) -> bool:
        """Get next reserve token"""
        if self._api_tokens_reserve:
            self._api_token = self._api_tokens_reserve.pop(0)
            return True

        return False

    def _make_request(self, url: str, params: dict) -> tuple[requests.Response, dict]:
        """Make request for VK API"""
        # make time delay for keep within RPS
        delay = self._api_rps_limit + self._time_last_request - time.time()
        if delay > 0:
            time.sleep(delay)

        while True:
            if params.get('access_token', ''):
                params['access_token'] = self._api_token  # set last api_token
            response = requests.get(url, params=params)
            try:
                data = response.json()
            except Exception:
                data = {}

            error_code = data.get('error', 0)
            if isinstance(error_code, dict):
                error_code = error_code.get('error_code', 0)
            if error_code == 5:  # user authorization failed
                if not self._get_reserve_token():
                    break
            else:
                break

        self._time_last_request = time.time()
        return response, data

    def _get_access_token_by_url(self) -> str:
        """Get API access token by generated URL"""
        params = {
            'client_id': self._app_id,
            'scope': self._app_scope,
            'redirect_uri': self._oauth_url + 'blank.html',
            'display': 'page',
            'response_type': 'token',
            'v': self._api_version,
        }

        response, data = self._make_request(self._oauth_url + 'authorize', params)
        if response.status_code == 200 and not data.get('error', ''):
            print(f"Open this page in your browser when you login in your vk account:\n{response.url}")
            url = input(f"Copy new URL from browser and paste here: ")
            token = ''
            start_index = url.find('access_token=')
            if start_index > 0:
                token = url[start_index + 13:]
                end_index = token.find('&')
                if end_index > 0:
                    token = token[:end_index]
                input("Below is your VK API access token. "
                      "You can copy and paste it into the code (VK_API_TOKEN), "
                      f"and use it the next time you run the script:\n{token}"
                      "\nPress any key to continue...")
            return token
        print("Error!!! Failed to obtain access token:", response.status_code, data.get('error', ''))
        return ''

    def get_id_user_groups(self, user_id: int) -> list[int]:
        """Get user's groups IDs by userID"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'user_id': user_id,
        }

        response, data = self._make_request(self._api_ulr + 'groups.get', params)
        if response.status_code == 200 and not data.get('error', ''):
            groups = data.get('response', {}).get('items', [])
            return groups
        print("Error!!! Failed to get user's groups IDs:", response.status_code, data.get('error', ''))
        return []

    def get_users_ids_by_query(self, query: str, count: int = 10) -> list[dict]:
        """Get users IDs by query"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'count': count,
            'q': query,
            'sort': 0,  # 0 - by popular, 1 - by date of registration
        }
        response, data = self._make_request(self._api_ulr + 'users.search', params)
        if response.status_code == 200 and not data.get('error', ''):
            users = data.get('response', {}).get('items', [])
            return users
        print("Error!!! Failed to get users by query:", response.status_code, data.get('error', ''))
        return []

    def get_groups_ids_by_query(self, query: str, count: int = 10) -> list[dict]:
        """Get groups IDs by query"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'count': count,
            'q': query,
            'sort': 0,  # 0 - equals vk.com, 6 - by followers count
        }
        response, data = self._make_request(self._api_ulr + 'groups.search', params)
        if response.status_code == 200 and not data.get('error', ''):
            groups = data.get('response', {}).get('items', [])
            return groups
        print("Error!!! Failed to get groups by query:", response.status_code, data.get('error', ''))
        return []

    def get_groups_users_by_query(self, query: str, count: int = 10, filters: str = '') -> list[dict]:
        """Get search (groups, users) by query"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'limit': count,
            'q': query,
            'filters': filters,  # 'groups' - only groups, '' - return users and groups
            'search_global': 1,  # 0 - only your account, 1 - global
        }
        response, data = self._make_request(self._api_ulr + 'search.getHints', params)
        if response.status_code == 200 and not data.get('error', ''):
            groups = data.get('response', {}).get('items', [])
            return groups
        print("Error!!! Failed to get groups by query:", response.status_code, data.get('error', ''))
        return []

    def get_user_friends(self, user_id: int) -> list[int]:
        """Get user's friends IDs by userID"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'user_id': user_id,
        }
        response, data = self._make_request(self._api_ulr + 'friends.get', params)
        if response.status_code == 200 and not data.get('error', ''):
            friends = data.get('response', {}).get('items', [])
            return friends
        print("Error!!! Failed to get user's friends IDs:", response.status_code, data.get('error', ''))
        return []

    def get_users_ids(self, screen_names: list[str | int]) -> list[int]:
        """Get user's ID's by screen_names/IDs"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'user_ids': ",".join(map(str, screen_names)),
        }
        response, data = self._make_request(self._api_ulr + 'users.get', params)
        if response.status_code == 200 and not data.get('error', ''):
            users = data.get('response', {})
            users_ids = [user.get('id') for user in users if user.get('id', None)]
            return users_ids
        print("Error!!! Failed to get user's IDs by screen names:", response.status_code, data.get('error', ''))
        return []

    def get_users_info(self, screen_names: list[str | int]) -> list[dict]:
        """Get user's info by screen_names/IDs"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'user_ids': ",".join(map(str, screen_names)),
            'fields': 'activities,about,blacklisted,blacklisted_by_me,books,bdate,can_be_invited_group,can_post,'
                      'can_see_all_posts,can_see_audio,can_send_friend_request,can_write_private_message,career,'
                      'common_count,connections,contacts,city,country,crop_photo,domain,education,exports,'
                      'first_name_nom,first_name_gen,first_name_dat,first_name_acc,first_name_ins,first_name_abl,'
                      'followers_count,friend_status,games,has_photo,has_mobile,home_town,interests,is_favorite,'
                      'is_friend,is_hidden_from_feed,is_no_index,last_name_nom,last_name_gen,last_name_dat,'
                      'last_name_acc,last_name_ins,last_name_abl,last_seen,maiden_name,military,movies,music,'
                      'nickname,occupation,online,personal,photo_100,photo_200,photo_200_orig,photo_400_orig,'
                      'photo_50,photo_id,photo_max,photo_max_orig,quotes,relation,relatives,schools,screen_name,'
                      'sex,site,status,timezone,trending,tv,universities,verified,wall_default'
        }
        response, data = self._make_request(self._api_ulr + 'users.get', params)
        if response.status_code == 200 and not data.get('error', ''):
            users = data.get('response', {})
            users_info = [{key: value for key, value in user.items() if value} for user in users]
            return users_info
        print("Error!!! Failed to get user's info by screen names:", response.status_code, data.get('error', ''))
        return []

    def get_groups_ids(self, screen_names: list[str | int]) -> list[dict]:
        """Get groups IDs by screen names/IDs"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'group_ids': ",".join(map(str, screen_names)),
        }
        response, data = self._make_request(self._api_ulr + 'groups.getById', params)
        if response.status_code == 200 and not data.get('error', ''):
            groups = data.get('response', {}).get('groups', {})
            groups_ids = [group.get('id') for group in groups if group.get('id', None)]
            return groups_ids
        print("Error!!! Failed to get groups IDs by screen names:", response.status_code, data.get('error', ''))
        return []

    def get_groups_info(self, screen_names: list[str | int]) -> list[dict]:
        """Get groups info by screen_names/IDs"""
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'group_ids': ",".join(map(str, screen_names)),
            'fields': 'activity,addresses,age_limits,ban_info,can_create_topic,can_message,can_post,can_suggest,'
                      'can_see_all_posts,can_upload_doc,can_upload_story,can_upload_video,city,contacts,counters,'
                      'country,cover,crop_photo,description,fixed_post,has_photo,is_favorite,is_hidden_from_feed,'
                      'is_messages_blocked,links,main_album_id,main_section,market,member_status,members_count,'
                      'place,public_date_label,site,start_date,finish_date,status,trending,verified,wall,wiki_page'
        }
        response, data = self._make_request(self._api_ulr + 'groups.getById', params)
        if response.status_code == 200 and not data.get('error', ''):
            groups = data.get('response', {}).get('groups', {})
            groups_info = [{key: value for key, value in group.items() if value} for group in groups]
            return groups_info
        print("Error!!! Failed to get groups info by screen names:", response.status_code, data.get('error', ''))
        return []

    def get_posts_info(self, screen_name: str | int, count: int = 30, is_user: bool = True,
                       is_hypertext: bool = True) -> list[dict]:
        """Get posts in user's/group's wall"""
        # Important! If the post contains a link to another user (#user) or url,
        # then in the response it will be presented in the following form: [id123456|user] or [url|user].
        # This affect the length of the resulting post text
        params = {
            'access_token': self._api_token,
            'v': self._api_version,
            'owner_id': 0 if isinstance(screen_name, str) else screen_name if is_user else -screen_name,
            'domain': screen_name if isinstance(screen_name, str) else '',
            'count': count,
            'filter': 'all',  # (suggests, postponed, owner, others, all, donut)
        }
        response, data = self._make_request(self._api_ulr + 'wall.get', params)
        if response.status_code == 200 and not data.get('error', ''):
            posts = data.get('response', {}).get('items', {})
            return posts
        print("Error!!! Failed to get posts in user's/group's wall:", response.status_code, data.get('error', ''))
        return []

    @staticmethod
    def get_field_from_data(data: list[dict], field: str,
                            filter_field: str = '',  # value will determine whether the element is suitable or not
                            filter_field_allowing: bool = True  # value which value of filter_field will be accepted
                            ) -> list:
        """Return one field from a list of data"""
        data_fields = [item.get(field) for item in data
                       if item.get(field, None)
                       and filter_field_allowing == item.get(filter_field, filter_field_allowing)]
        return data_fields


if __name__ == "__main__":
    import datetime

    MONTH_AMOUNT = 3
    SYMBOLS_AMOUNT = 400
    POSTS_AMOUNT = 1

    def check_post_by_symbols_amount(post: dict, symbols_amount: int) -> bool:
        """Checks post's text is greater than symbols_amount"""
        return len(post.get('text', '')) > symbols_amount

    def check_post_by_date_amount(post: dict, month_amount: int) -> bool:
        """Check post is not older than month_amount"""
        post_time = datetime.datetime.fromtimestamp(post.get('date', 0))
        now_time = datetime.datetime.now()
        time_delta = datetime.timedelta(month_amount * 365 / 12)
        return post_time + time_delta >= now_time

    def remove_hypertext(text: str) -> str:
        """Remove from post url-links, hypertext"""
        # delete VK-post's hypertext: [...|...]
        clear_text = re.sub(r'\[[^\[\|\]]+\|[^\[\|\]]+\]', '', text)
        # delete url-links
        clear_text = re.sub(
            r'(http://|https://|www.)(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            '', clear_text)
        return clear_text

    vk_api = VK(
        api_url=VK_API_URL,
        oauth_url=VK_OAUTH_URL,
        api_version=VK_API_VERSION,
        api_rps_limit=VK_API_RPS_LIMIT,
        api_token=VK_API_TOKEN,
        api_tokens_reserve=VK_API_RESERVE_TOKENS,
        app_id=VK_APP_ID,
        app_scope=VK_APP_SCOPE,
    )

    # search groups by query
    core_for_search = input("Input a search term to find communities: ")
    if core_for_search:
        # search groups and users by query - variant 1
        # search = vk_api.get_groups_users_by_query(core_for_search)
        # groups = VK.get_field_from_data(search, 'group')
        # groups_ids = VK.get_field_from_data(groups, 'id', 'is_closed', False)
        # users = VK.get_field_from_data(search, 'profile')
        # users_ids = VK.get_field_from_data(users, 'id', 'is_closed', False)

        # search groups by query - variant 2
        groups = vk_api.get_groups_ids_by_query(core_for_search)
        groups_ids = VK.get_field_from_data(groups, 'id', 'is_closed', False)

        # search users by query - variant 2
        users = vk_api.get_users_ids_by_query(core_for_search)
        users_ids = VK.get_field_from_data(users, 'id', 'is_closed', False)
    else:
        groups_ids = ['vk', 'dedmoroz']
        users_ids = [53083705, 'id302262930']

    groups_and_users = [(group, False) for group in groups_ids] + [(user, True) for user in users_ids]

    # get posts and filtering
    for user, is_user in groups_and_users:
        user_name = ''
        user_type = ''
        if is_user:
            user_info = vk_api.get_users_info([user])
            if user_info:
                user_type = 'пользователя'
                user_name = user_info[0].get('first_name_gen', '') + ' ' + user_info[0].get('last_name_gen', '')
        else:
            group_info = vk_api.get_groups_info([user])
            if group_info:
                is_user = False
                user_type = 'сообщества'
                user_name = group_info[0].get('name', '')

        posts = vk_api.get_posts_info(user, count=30, is_user=is_user)
        if posts:
            filtered_posts = [remove_hypertext(post.get('text', '')) for post in posts
                              if check_post_by_symbols_amount(post, SYMBOLS_AMOUNT)
                              and check_post_by_date_amount(post, MONTH_AMOUNT)
                              and not post.get('is_pinned', 0)]
            if filtered_posts:
                print(f"{'=' * 21} Посты {user_type} {user_name}: {'=' * 21}")
                for index, post in enumerate(filtered_posts):
                    print('\n', '*'*20, f"Пост №{index+1}", '*'*20, '\n', post)
                    if index+1 >= POSTS_AMOUNT:
                        break
                print('_' * 100, '\n\n')
