import sys, xbmcgui, xbmcplugin, xbmcaddon
import os, requests, re, json
from urllib import urlencode, quote_plus 
from urlparse import parse_qsl
import pickle
import inputstreamhelper

addon           = xbmcaddon.Addon(id='plugin.video.ufc')
addon_url       = sys.argv[0]
addon_handle    = int(sys.argv[1])
addon_icon      = addon.getAddonInfo('icon')
addon_BASE_PATH = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
#TOKEN_FILE = os.path.join("/tmp/","auth_token.txt")

TOKEN_FILE = xbmc.translatePath(os.path.join('special://temp','ufc_token_data.txt'))


urls = {
        "home" : "https://dce-frontoffice.imggaming.com/api/v2/content/home?bpp=10&bp=1&rpp=25&displayGeoblockedLive=false&displaySectionLinkBuckets=show",
        "library" : "https://dce-frontoffice.imggaming.com/api/v2/content/browse?bpp=10&bp=1&rpp=25&displaySectionLinkBuckets=show",
        "live" : "https://dce-frontoffice.imggaming.com/api/v2/event/live?rpp=4",
        "favourites" : "https://dce-frontoffice.imggaming.com/api/v2/favourite/vods?rpp=25",
        "history": "https://dce-frontoffice.imggaming.com/api/v2/customer/history/vod?p=1&rpp=25"
        }

auth_url = "https://dce-frontoffice.imggaming.com/api/v2/login"
playlist_url = "https://dce-frontoffice.imggaming.com/api/v2/vod/playlist/{0}?rpp=25&p=1"


headers={
    "content-type": "application/json",
    "realm": "dce.ufc",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "x-api-key": "857a1e5d-e35e-4fdf-805b-a87b6f8364bf"
  }

def get_creds():
    """Get username and password. Return dict of username and password"""

    if len(addon.getSetting('username')) == 0 or len(addon.getSetting('password')) == 0:
        return None

    return {
        'username': addon.getSetting('username'),  
        'password': addon.getSetting('password')
    }

def get_auth_token():
    """Take in the credentials as dict['username', 'password'] and return the Auth token as string with the bearer keyword ready to be used in the header"""
    creds = get_creds()
    credentials = json.dumps({"id":creds['username'],"secret":creds['password']})

    session = requests.Session()
    session.headers = headers
    response = session.post(auth_url, data=credentials)

    if response.status_code == 201:
        token = "Bearer " + response.json()["authorisationToken"]
        session.close()
        return token
    else:
        xbmc.log("Could not get Auth Token, Session text: {0}".format(str(session.json())),level=xbmc.LOGERROR)
        return False


def get_web_data(url, put_data=None):
    """Grab the web data from the url"""
    token = get_token()

    session = requests.Session()
    headers_this_session = headers
    headers_this_session["authorization"] = token
    session.headers = headers_this_session
    
    if not put_data:
        response = session.get(url, headers=headers_this_session)
    else:
        response = session.post(url,headers=headers_this_session, data=put_data)    

    
    if response.status_code < 400:
        return response.json()
    elif response.status_code == 401:  #if the token gives back unauthorized, it's old. Delete it and rerun the method
        os.remove(TOKEN_FILE)
        get_web_data(url)
    else:
        xbmc.log("Could not get data, line 80. Response: {0}\r\nText: {1}".format(response.status_code, response.text),level=xbmc.LOGERROR)
        return None

def get_token():
    """Get the token either from the file saved or by getting a new one if the file doesn't exist"""
    if not os.path.isfile(TOKEN_FILE): #if bearer token file does not exist
        token = get_auth_token()
    else:
        token = pickle.load(open(TOKEN_FILE, 'rb'))

    return token


def router(paramstring):
    """Router for kodi to select the menu item and route appropriately. """ 
    params = dict(parse_qsl(paramstring))
    
    if params:
        action = params['action']
        if action == 'listing':
            menu_data=get_categories(params['u'])
            build_menu(menu_data)
        elif action == 'play':
            play_hls_video(params['i'],params['t'])
        elif action == 'search':
            search_term = get_search_term()
            menu_data = search(search_term)
            build_menu(menu_data)        
        else:
            pass
    else:
        build_initial_menu()




def get_categories(url):
    """Put items into readable array of dict, and return the array for building the menu"""
    data = get_web_data(url) ###Scrape the url data

    keywords = ["contentList","vods","events"]
    
    extract = []
    for keyword in keywords:
        iter_object = gen_dict_extract(keyword, data) ##create the iter object
        
        for half_parsed_list in iter_object: #
            extract.append(half_parsed_list)
    
    clean_extract = clean_iter_data(extract)
 
    my_listings = []
    for i in clean_extract:        
        if i.get("type") == 'PLAYLIST':
            #/xbmc.log(str(i), level=xbmc.LOGERROR)
            listing = {
                'type' : i.get("type"),
                'coverUrl' : i.get("coverUrl"),
                'smallCoverUrl' : i.get("smallCoverUrl"),
                'title' : i.get("title"),
                'description' : i.get("description"),
                'id' : i.get("id")
                }
            my_listings.append(listing)
        if i.get("type") == 'VOD':
            listing = {
                'type' : i.get("type"),
                'thumbnailUrl' : i.get("thumbnailUrl"),
                #'posterUrl' : i.get("posterUrl"),
                'duration' : i.get("duration"),
                'title' : i.get("title"),
                'description' : i.get("description"),
                'id' : i.get("id"),
                'duration' : i.get("duration")
                }
            if i.get("posterUrl"):
                listing["posterUrl"] = i.get("posterUrl")
            else:
                listing["posterUrl"] = listing["thumbnailUrl"]
            my_listings.append(listing)

        if i.get("type") == "LIVE" and i.get("live") == True:
            listing = {
                'type' : i.get("type"),
                'coverUrl' : i.get("thumbnailUrl"),
                'thumbnailUrl' : i.get("thumbnailUrl"),
                'smallCoverUrl' : i.get("thumbnailUrl"),
                'title' : i.get("title"),
                'description' : i.get("description"),
                'id' : i.get("id")
                }
            if i.get("posterUrl"):
                listing["posterUrl"] = i.get("posterUrl")
            else:
                listing["posterUrl"] = listing["thumbnailUrl"]
            my_listings.append(listing)



    return my_listings

def get_search_term():
    """Get search term to use in search funtion"""
    kb = xbmc.Keyboard('default', 'heading')
    kb.setDefault('')
    kb.setHeading('Search')
    kb.setHiddenInput(False)
    kb.doModal()
    if (kb.isConfirmed()):
        search_term = kb.getText()
        return search_term
    else:
        return


#### For use in search
def search(query_string):
    """Search funtion, takes in keyword for search then returns a list of items that can be used to create the menu"""
   
    search_url = """https://h99xldr8mj-1.algolianet.com/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(3.35.1)%3B%20Browser&x-algolia-application-id=H99XLDR8MJ&x-algolia-api-key=e55ccb3db0399eabe2bfc37a0314c346"""

    post_data="{\"requests\":[{\"indexName\":\"prod-dce.ufc-livestreaming-events\",\"params\":\"query=" + query_string + "&facetFilters=%5B%22type%3AVOD_VIDEO%22%5D&hitsPerPage=10\"}]}"    

    data = get_web_data(search_url,put_data=post_data) 

    keywords = ["hits"]

    extract = []
    for keyword in keywords:
        iter_object = gen_dict_extract(keyword, data) ##create the iter object

        for half_parsed_list in iter_object: #
            extract.append(half_parsed_list)

    clean_extract = clean_iter_data(extract)

 
    my_list = []
    
    for item in clean_extract:
        
        list_item = {}
        
        if type(item) is dict:
            if 'VOD' in item.get("type"):    #'PLAYLIST': 
                list_item["type"] = 'VOD'
                list_item["id"]  = item["id"]                
                list_item["duration"] = item["duration"]
                if "localisations" in item.keys():
                    if "en_US" in item["localisations"]:
                        list_item["title"] = str(item["localisations"]["en_US"]["title"])

                    if "en_GB" in item["localisations"]:
                        list_item["title"] = str(item["localisations"]["en_GB"]["title"])                        

                else:
                    list_item["title"] = str(item["title"])  


                if "thumbnailUrl" in item.keys():
                    list_item["thumbnailUrl"] = str(item["thumbnailUrl"])

                else:
                    list_item["thumbnailUrl"] = str(item["smallCoverUrl"])
                    
                my_list.append(list_item)

    return my_list



def clean_iter_data(data):
    """Takes in iter data which is mess and returns list of dict items"""
    newlist = []
    newlist = [item for data in data for item in data]
    return_list = []    
    for item in newlist:
        if type(item) is dict:
            return_list.append(item)

    return return_list
            
                
def build_menu(itemData):     
    """ Takes in array of dict, using this array builds a menu to display in Kodi"""
    for my_item in itemData:
    
        if any(my_item["type"] in s for s in ('VOD' ,'LIVE')):
            kodi_item = xbmcgui.ListItem(label=my_item["title"],label2=my_item.get("description"))
            kodi_item.setArt({  'thumb': my_item.get("thumbnailUrl"), 
                                'icon' :  my_item.get("thumbnailUrl"), 
                                'landscape': my_item.get("posterUrl"), 
                                'poster' : my_item.get("posterUrl"), 
                                'banner': my_item.get("posterUrl"), 
                                'fanart': my_item.get("posterUrl")})

            video_info = {
                            'plot': my_item.get("description"),
                            'plotoutline' : my_item.get("description"),
                            'tagline' : my_item.get("description"),
                            'setoverview' : my_item.get("description"),
                            'episodeguide' : my_item.get("description"),
                            'mediatype' : "tvshow",
                            'duration': my_item.get("duration")
                           }

            kodi_item.setInfo(type='video', infoLabels=video_info)
                                
            url = '{0}?action=play&i={1}&t={2}'.format(addon_url, my_item["id"], quote_plus(my_item["title"].encode('utf8'))) ##added encode utf
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, isFolder=False, totalItems=len(itemData)) ###last false is if it is a directory
    
        elif my_item["type"] == 'PLAYLIST':
            #xbmc.log("Item type is playlist ",level=xbmc.LOGERROR)
            #xbmc.log(str(my_item["type"]),level=xbmc.LOGERROR)
            kodi_item = xbmcgui.ListItem(label=my_item["title"],label2=my_item.get("description"))

            kodi_item.setArt({  'thumb': my_item.get("smallCoverUrl"),
                                'icon' :  my_item.get("smallCoverUrl"),
                                'landscape': my_item.get("coverUrl"),
                                'poster' : my_item.get("coverUrl"),
                                'banner': my_item.get("coverUrl"),
                                'fanart': my_item.get("coverUrl")})

            url_for_getting_data = playlist_url.format(my_item["id"])
            url = '{0}?action=listing&u={1}'.format(addon_url, url_for_getting_data)
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, isFolder=True, totalItems=len(itemData)) ###last false is if it is a directory 

    ###Thats it create the folder structure
    xbmcplugin.endOfDirectory(addon_handle)



def build_initial_menu():
    """Builds the initial menus for UFC"""

    for item in urls:   
        kodi_item = xbmcgui.ListItem(label=item.capitalize())
        info_label = {
                        'title' : item.capitalize(),
                        'plot': "UFC {0}".format(str(item))
                        }
        kodi_item.setInfo(type='video', infoLabels=info_label )
        url = '{0}?action=listing&u={1}'.format(addon_url, urls[item])
        xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, True ) ###last false is if it is a directory

    #### Add the search to the list also:
    kodi_item = xbmcgui.ListItem(label="Search")
    kodi_item.setInfo(type='video', infoLabels={'title': 'Search'})
    url = '{0}?action=search'.format(addon_url)
    xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, True ) ###last false is if it is a directory


    ##create the initialm Menu
    xbmcplugin.endOfDirectory(addon_handle)



def gen_dict_extract(key, var):
    """Find all items with value "key" in dict var, and return an iterable with all the key items, need to iter using
        for x in generator, x[0]"""
    if hasattr(var,'items'):   
        for k, v in var.items():
            if k in key:             
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):                   
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):     
                        yield result

def play_hls_video(v_id, v_title):

    status, stream, subtitles = publish_point({'id': v_id })

    if status == 400:
        if post_auth(get_creds()):
            status, stream = publish_point({ 'id': v_id })
        else:
            dialog = xbmcgui.Dialog()
            dialog.ok('Authorization Error', 'Authorization to UFC Fight Pass failed.')

    #v_token = get_token()

    encode_string = {"User-Agent": headers["user-agent"],
                    "Accept":"*/*",
                    "Accept-Encoding":"gzip, deflate, br",
                    "Accept-Language":"en-US,en;q=0.9",
                    "Connection":"keep-alive",
                    "Origin":"https://ufcfightpass.com",
                    "Sec-Fetch-Mode":"cors",
                    "Sec-Fetch-Site":"cross-site"
                    }

    my_encoding = urlencode(encode_string)

    is_helper = inputstreamhelper.Helper('hls')
    if is_helper.check_inputstream():

        playitem = xbmcgui.ListItem(path=stream,label=v_title)
        playitem.setProperty('isFolder', 'false')
        playitem.setPath(path=stream)
        playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        playitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
        playitem.setProperty('inputstream.adaptive.stream_headers',my_encoding)
        playitem.setContentLookup(False)
        playitem.setSubtitles(subtitles)

        xbmc.Player().play(stream,  playitem)
                        
                        
                        
def publish_point(video):
    """??Takes in Video Dict, queries website publishpoint with video info (video id), 
    get a response that includes a path,returns (status code, path to video)"""
    
    url = 'https://dce-frontoffice.imggaming.com/api/v2/stream/vod/'
    url2 = 'https://dce-frontoffice.imggaming.com/api/v2/event/' ##This url is for streaming (grab the data)a
    url3 = 'https://dce-frontoffice.imggaming.com/api/v2/stream?eventId=' ##another url for stremaing (actual streaming info)
    start_url = "" ## Start url string for final response. 
    
    s = requests.Session()
    header_this_session = headers
    header_this_session["authorization"] = str(get_token())
    s.headers = header_this_session
    
    
    resp = s.get(url+str(video['id']), headers=header_this_session) #changed params=payload to params=str(video['id'])
    # normally status 400 if have an expired session
    status = resp.status_code


    if status != 200: ##hack to deal with live using a different url
        resp = s.get(url3+str(video['id']), headers=header_this_session) 
        result = resp.json()
        
 
    result = resp.json()
    if not result:
        return status, None

    resp2 = s.get(result['playerUrlCallback'], headers = header_this_session)
    status2 = resp2.status_code
    result2= resp2.json()
    
    try:
        o_path = result2["hls"]["url"]   ###this is the m3u8 url
        start_url = o_path
    except:
        o_path = result2['hlsUrl']
        start_url = o_path
    
    subtitles = []    
    if "subtitles" in result2.keys():
        for item in result2["subtitles"]:
            subtitles.append(item["url"])
   





   
    return status2, start_url, subtitles  ##Remove this if it doesn't work at later stage



if __name__ == '__main__':     
    router(sys.argv[2][1:])

