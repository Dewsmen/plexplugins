# -*- coding: utf-8 -*-
import re
###################################################################################
# 
# This work is licensed under a Creative Commons Attribution 3.0 Unported License.
# See http://creativecommons.org/licenses/by/3.0/deed.en_US for detail.
#
###################################################################################

WATCHIS_URL			= 'http://watch.is'
WATCHIS_VIDEOS		= '%s/api/?genre=%%d&page=%%d' % WATCHIS_URL
WATCHIS_BOOKMARKS	= '%s/api/bookmarks?page=%%d' % WATCHIS_URL
WATCHIS_TOP			= '%s/api/top' % WATCHIS_URL
WATCHIS_GENRES		= '%s/api/genres' % WATCHIS_URL
WATCHIS_SEARCH		= '%s/api/?search=%%s&page=%%d' % WATCHIS_URL
WATCHIS_LOGIN		= '%s/api/?username=%%s&password=%%s' % WATCHIS_URL
WATCHIS_SESSION_EXP	= 7


ICON 				= 'icon-default.png'
ART 				= 'art-default.jpg'
ICON 				= 'icon-default.png'
PREFS 				= 'icon-prefs.png'
SEARCH 				= 'icon-search.png'

####################################################################################################
def Start():
	
	Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')

	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = 'WatchIs'

	DirectoryObject.thumb = R(ICON)
	NextPageObject.thumb = R(ICON)

	PrefsObject.thumb = R(PREFS)
	PrefsObject.art = R(ART)

	InputDirectoryObject.thumb = R(SEARCH)
	InputDirectoryObject.art = R(ART)

	HTTP.CacheTime = CACHE_1HOUR
####################################################################################################
def ValidatePrefs():
	# Dewsmen 11/13/2014:in some case get error 'OSError: Directory is not empty'
	try: 
		HTTP.ClearCache()
		HTTP.ClearCookies()
	except:
		Log ("Can't clear cache, please clean it manually")
####################################################################################################
@handler('/video/watchis', 'WatchIs', thumb=ICON, art=ART)
def MainMenu():

	# Dewsmen 11/14/2014: Added new level MenuItem to check Login and prevent anuthorizer response cache'
	oc = ObjectContainer(
		view_group = 'InfoList',
		objects = [
			DirectoryObject(
				key		= Callback(MenuItem, item = 'GetVideos', title=uL('Main'), url=WATCHIS_VIDEOS),
				title	= uL('Main'),
				summary	= uL('Main Page')
			),
			DirectoryObject(
				key		= Callback(MenuItem, item = 'GetVideosTop', title=uL('Top'), url=WATCHIS_TOP),
				title	= uL('Top'),
				summary	= uL('Top Rated Videos')
			),
			DirectoryObject(
				key		= Callback(MenuItem, item = 'Genres', title=uL('Genres'), url=WATCHIS_GENRES),
				title	= uL('Genres'),
				summary	= uL('Genre Categories')
			),
			DirectoryObject(
				key		= Callback(MenuItem, item = 'GetBookmarks', title=uL('Bookmarks'), url=WATCHIS_BOOKMARKS),
				title	= uL('Bookmarks'),
				summary	= uL('Bookmarks Page')
			),
			InputDirectoryObject(
				key		= Callback(MenuItem, item = 'Search', title=uL('Search'), url=WATCHIS_SEARCH),
				title	= uL('Search'),
				prompt	= uL('Search')
			),
			PrefsObject(
				title	= uL('Preferences...'),
				thumb 	= PREFS,
				art 	= ART 
			)
		]
	)

	return oc

####################################################################################################
@route('/video/watchis/MenuItem/{item}')
def MenuItem(item, title, url, query=''):

	# See if we need to log in
	if not LoggedIn():
		# See if we have any creds stored
		if not Prefs['username'] or not Prefs['password']:
			return ObjectContainer(header= uL('Error'), message=uL('Please enter your email and password in the preferences'))

		# Try to log in
		Login()

		# Now check to see if we're logged in
		if not LoggedIn():
			return ObjectContainer(header=uL('Error'), message=uL('Please enter your correct email and password in the preferences'), title1 = uL('Access Denied'))

	if item == 'GetVideos':
		oc = GetVideos(title, url)
	elif item == 'GetVideosTop':
		oc = GetVideosTop(title, url)
	elif item == 'Genres':
		oc = Genres(title, url)
	elif item == 'GetBookmarks':
		oc = GetBookmarks(title, url)
	elif item == 'Search':
		oc =  Search(title=title, url=url, query = query)

	return oc
####################################################################################################
@route('/video/watchis/videos', genre=int, page=int, cacheTime=int, allow_sync=True)
def GetVideos(title, url, genre=0, page=0, cacheTime=CACHE_1HOUR):

	ObjectContainer(header = uL("No More Videos"), message = uL("No more videos are available..."))

	oc, nextPage = GetVideosUrl(title, url%(genre, page), cacheTime)

	if oc.header == uL('Error'):
		return oc
	# It appears that sometimes we expect another page, but there ends up being no valid videos available
	if len(oc) == 0 and page > 0:
		return ObjectContainer(header = uL("No More Videos"), message = uL("No more videos are available..."))

	if nextPage:
		cbKey = Callback(GetVideos, title=title, url=url, genre=genre, page=page + 1, cacheTime=cacheTime)
		PutNextPage(oc, cbKey)
	return oc

####################################################################################################
@route('/video/watchis/videos_top', allow_sync=True)
def GetVideosTop(title, url, cacheTime=CACHE_1HOUR):
	oc, nextPage = GetVideosUrl(title, url, cacheTime)
	return oc

####################################################################################################
# We add a default query string purely so that it is easier to be tested by the automated channel tester
@route('/video/watchis/search', page=int, cacheTime=int, allow_sync=True)
def Search(query, title, url, page=0, cacheTime=1):

	searchUrl = url % (String.Quote(query, usePlus = True), page)

	oc, nextPage = GetVideosUrl(title, searchUrl)
	if oc.header == uL('Error'):
		return oc

	if len(oc) == 0:
		if page > 0:
			return ObjectContainer(header = uL("No More Videos"), message = uL("No more videos are available..."))
		else:
			return ObjectContainer(header = uL("No Results"), message = uL("No videos found..."))
	
	if nextPage:	
		PutNextPage(oc, Callback(Search, query=query, title=title, url=url, page=page + 1, cacheTime=cacheTime))
	return oc

####################################################################################################
@route('/video/watchis/genres', 'Genres')
def Genres(title, url):

	oc = ObjectContainer(title2=unicode(title), view_group='List')

	# Dewsmen 11/13/2014: some OSs and browsers doesn't allow cookie, so add them manually
	xml = XML.ElementFromURL(url, cacheTime=CACHE_1WEEK, headers = Dict['Cookie'])
	errorOC = CheckError(xml, '//genres/item')
	if errorOC:
		#Response.Status = 404
		return errorOC

	genres = xml.xpath('//genres/item')

	for genre_el in genres:
		genreString = XML.StringFromElement(genre_el)
		genre = XML.ObjectFromString(genreString)
		genre_id = int(genre['id'])
		genre_title = unicode(str(genre['title']))

		oc.add(DirectoryObject(
			key = Callback(GetVideos, title=genre_title, url=WATCHIS_VIDEOS, genre=genre_id),
			title = genre_title
		))

	return oc

####################################################################################################
@route('/video/watchis/bookmarks', genre=int, page=int, cacheTime=int, allow_sync=True)
def GetBookmarks(title, url, page=0, cacheTime=0):

	oc, nextPage = GetVideosUrl(title, url % page, cacheTime)
	if oc.header == uL('Error'):
		return oc
	# It appears that sometimes we expect another page, but there ends up being no valid videos available
	if len(oc) == 0 and page > 0:
		return ObjectContainer(header = uL("No More Videos"), message = uL("No more videos are available..."))

	if nextPage:
		cbKey = Callback(GetBookmarks, title=title, url=url, genre=genre, page=page + 1, cacheTime=cacheTime)
		PutNextPage(oc, cbKey)
	return oc

####################################################################################################
def GetVideosUrl(title, url, cacheTime=CACHE_1HOUR):

	oc = ObjectContainer(title2=uL(title), view_group='InfoList')

	xml = XML.ElementFromURL(url, cacheTime=cacheTime, headers = Dict['Cookie'])

	total = xml.get("total")
	if total:
		total = int(xml.get("total"))
		page = int(xml.get("page"))
		pageSize = int(xml.get("pageSize"))
		nextPage = True if total > (page*pageSize+pageSize) else False
		if total == 0:
			return oc, nextPage
	else:
		nextPage = False

	errorOC = CheckError(xml, '//catalog/item')
	if errorOC:
		#Response.Status = 404
		return errorOC, nextPage

	results = {}
	@parallelize
	def GetAllVideos():
		videos = xml.xpath('//catalog/item')
		for num in range(len(videos)):
			video = videos[num]
			@task
			def GetVideo(num=num, video=video, results=results):
				try:
					itemString = XML.StringFromElement(video)
					item = XML.ObjectFromString(itemString)

					video_id = item['id']
					
					#parser cannot parse item['url'] for some reason
					url = '%s/api/watch/%s' % (WATCHIS_URL, video_id)
					posterUrl = '%s/posters/%s.jpg' % (WATCHIS_URL, video_id)

					#11/22/2014 Dewsmen Cheat for service based on https://forums.plex.tv/index.php/topic/88220-data-api-available-in-service-code/
					urlWithCookie = '%s#%s' %  (url, Dict['Cookie'])

					descXml = XML.ElementFromURL(url, cacheTime=cacheTime, headers = Dict['Cookie'])
					errorOC = CheckError(xml, '//item')
					if errorOC:
						#Response.Status = 404
						return
					descString = XML.StringFromElement(descXml.xpath('//item')[0])
					desc = XML.ObjectFromString(descString)

					results[num] = VideoClipObject(
						url = urlWithCookie,
						title = unicode(str(item['title'])),
						year = int(item['year']),
						summary = str(desc['about']),
						genres = [str(desc['genre'])],
						directors = [str(desc['director'])],
						countries = [str(desc['country'])],
						duration = TimeToMs(str(desc['duration'])),
						thumb = Resource.ContentsOfURLWithFallback(posterUrl, fallback='icon-default.png')
					)
				except:
					Log.Exception("Error!")
					return

	try: 
		keys = results.keys()
		keys.sort()

		for key in keys:
			oc.add(results[key])

	except:
		Log.Exception("Error!")
		return oc, nextPage

	return oc, nextPage

####################################################################################################
def PutNextPage(objCont, cbKey):
	objCont.add(NextPageObject(
		key = cbKey,
		title = uL('More...')
	))

####################################################################################################
def CheckError(xml, xpath):

	# See if we have any creds stored
	if not Prefs['username'] or not Prefs['password']:
		return ObjectContainer(header=uL('Error'), message=unicode("Empty Prefs." + ". " + uL('Please enter your email and password in the preferences')))

	#check response format
	responseText = xml.xpath(xpath)
	if not responseText:
		return ObjectContainer(header=uL('Error'), message=uL('Unexpected response from the Server. Please try later.'))

	errorText = xml.xpath('//error/text()')

	if errorText:
		if errorText[0] == 'Access Denied':
			return ObjectContainer(header=uL('Error'), title1 = uL(errorText[0]), message=uL(errorText[0]) + ". " + uL('Please enter your correct email and password in the preferences'))
		if errorText[0] == 'Search Error':
			return ObjectContainer(header=uL('Error'), title1 = uL(errorText[0]), message=uL('Search error'))
		return ObjectContainer(header=uL('Error'), message=uL(errorText[0]))

	return None

####################################################################################################
@route('/video/watchis/login')
def Login():

	Log(' --> Trying to log in')	
	HTTP.ClearCookies()

	# Dewsmen 11/21/2014 Reset Dict with cookie and session_start
	Dict.Reset()

	url = WATCHIS_LOGIN % (Prefs['username'], Prefs['password'])

	# Dewsmen 11/13/2014: don't need any response body on login, so change it from GET to HEAD
	# disabled cache for login 
	login = HTTP.Request(url, headers = {'Method': 'HEAD'}, cacheTime=0).headers
	
	cookies = HTTP.CookiesForURL(WATCHIS_URL + "/api/")

	# Dewsmen 11/13/2014: some OSs(found in FreeBSD) don't save cookies, so store and add them manually
	Dict['Cookie'] = {'Cookie':cookies}

	# Dewsmen 11/21/2014 Can't access cookie expire date, so will store response date that is 7 days less then expiration 
	Dict['SESSION_STARTED'] = login['Date']

#	if not LoggedIn():
#		Response.Status = 401 #Unauthorized

####################################################################################################
def LoggedIn():

	# Dewsmen 11/21/2014 added session expiration control

	#Dewsmen for old plugins without SESSION_STARTED force Login
	if not 'SESSION_STARTED' in Dict:
		return False

	sessionStarted = Datetime.ParseDate(Dict['SESSION_STARTED'])
	expDelta = Datetime.Delta(days = WATCHIS_SESSION_EXP)
	expDate = sessionStarted + expDelta 
	#if expiered force Login
	if expDate < Datetime.Now():
		return False

	#Dewsmen on wrong login still getting 200 OK, the only way to test - compare cookies
	match = re.match("(?=.*?username)(?=.*?group_id)(?=.*?password)(?=.*?uid)(?=.*?verification)(?=.*?PHPSESSID).*$", str(Dict['Cookie']))
	if match:
		return True
	else:
		return False

####################################################################################################
def TimeToMs(timecode):
	duration = timecode[ : -7]
	seconds = int(duration) * 60
	return seconds * 1000
####################################################################################################
def uL(text):
	return unicode(L(text))
