# -*- coding: utf-8 -*-

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

	Login()

####################################################################################################
def ValidatePrefs():
	# Dewsmen 11/13/2014: clear cache and cookie moved to Login()
	#HTTP.ClearCookies()
	#HTTP.ClearCache()
	Login()

####################################################################################################
@handler('/video/watchis', 'WatchIs', thumb=ICON, art=ART)
def MainMenu():
	oc = ObjectContainer(
		view_group = 'InfoList',
		objects = [
			DirectoryObject(
				key		= Callback(GetVideos, title=unicode(L('Main')), url=WATCHIS_VIDEOS),
				title	= unicode(L('Main')),
				summary	= unicode(L('Main Page'))
			),
			DirectoryObject(
				key		= Callback(GetVideosTop, title=unicode(L('Top')), url=WATCHIS_TOP),
				title	= unicode(L('Top')),
				summary	= unicode(L('Top Rated Videos'))
			),
			DirectoryObject(
				key		= Callback(Genres, title=unicode(L('Genres')), url=WATCHIS_GENRES),
				title	= unicode(L('Genres')),
				summary	= unicode(L('Genre Categories'))
			),
			DirectoryObject(
				key		= Callback(GetBookmarks, title=unicode(L('Bookmarks')), url=WATCHIS_BOOKMARKS),
				title	= unicode(L('Bookmarks')),
				summary	= unicode(L('Bookmarks Page'))
			),
			InputDirectoryObject(
				key		= Callback(Search, title=unicode(L('Search')), url=WATCHIS_SEARCH),
				title	= unicode(L('Search')),
				prompt	= unicode(L('Search'))
			),
			PrefsObject(
				title	= unicode(L('Preferences...')),
				thumb	= R('icon-prefs.png')
			)
		]
	)

	return oc

####################################################################################################
# We add a default query string purely so that it is easier to be tested by the automated channel tester
@route('/video/watchis/search', page=int, cacheTime=int, allow_sync=True)
def Search(query, title, url, page=0, cacheTime=1):
	oc, nextPage = GetVideosUrl(title, url % (query, page))
	if oc.header == unicode(L('Error')):
		return oc

	if len(oc) == 0:
		if page > 0:
			return ObjectContainer(header = unicode(L("No More Videos")), message = unicode(L("No more videos are available...")))
		else:
			return ObjectContainer(header = unicode(L("No Results")), message = unicode(L("No videos found...")))
	
	if nextPage:	
		PutNextPage(oc, Callback(Search, query=query, title=title, url=url, page=page + 1, cacheTime=cacheTime))
	return oc

####################################################################################################
@route('/video/watchis/genres', 'Genres')
def Genres(title, url):
	oc = ObjectContainer(title2=unicode(title), view_group='List')

	# Dewsmen 11/13/2014: some OSs and browsers doesn't allow cookie, so add them manually
	xml = XML.ElementFromURL(url, cacheTime=CACHE_1WEEK, headers = Dict['Cookie'])
	errorOC = CheckError(xml)
	if errorOC:
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
	if oc.header == unicode(L('Error')):
		return oc
	# It appears that sometimes we expect another page, but there ends up being no valid videos available
	if len(oc) == 0 and page > 0:
		return ObjectContainer(header = unicode(L("No More Videos")), message = unicode(L("No more videos are available...")))

	if nextPage:
		cbKey = Callback(GetBookmarks, title=title, url=url, genre=genre, page=page + 1, cacheTime=cacheTime)
		PutNextPage(oc, cbKey)
	return oc

####################################################################################################
@route('/video/watchis/videos', genre=int, page=int, cacheTime=int, allow_sync=True)
def GetVideos(title, url=WATCHIS_VIDEOS, genre=0, page=0, cacheTime=CACHE_1HOUR):
	oc, nextPage = GetVideosUrl(title, url%(genre, page), cacheTime)

	if oc.header == unicode(L('Error')):
		return oc
	# It appears that sometimes we expect another page, but there ends up being no valid videos available
	if len(oc) == 0 and page > 0:
		return ObjectContainer(header = unicode(L("No More Videos")), message = unicode(L("No more videos are available...")))

	if nextPage:
		cbKey = Callback(GetVideos, title=title, url=url, genre=genre, page=page + 1, cacheTime=cacheTime)
		PutNextPage(oc, cbKey)
	return oc

####################################################################################################
@route('/video/watchis/videos_top', cacheTime=int, allow_sync=True)
def GetVideosTop(title, url, cacheTime=CACHE_1HOUR):
	oc, nextPage = GetVideosUrl(title, url, cacheTime)
	return oc

####################################################################################################
def GetVideosUrl(title, url, cacheTime=CACHE_1HOUR):
	oc = ObjectContainer(title2=unicode(title), view_group='InfoList')

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
		
	#Dewsmen 11/13/2014: Doesn't work if total is 0, moved into prev if statement
	#if total and total == '0':
	#	return oc, nextPage

	errorOC = CheckError(xml)
	if errorOC:
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

					descXml = XML.ElementFromURL(url, cacheTime=cacheTime, headers = Dict['Cookie'])
					errorOC = CheckError(xml)
					if errorOC:
						return
					descString = XML.StringFromElement(descXml.xpath('//item')[0])
					desc = XML.ObjectFromString(descString)

					results[num] = VideoClipObject(
						url = url,
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
		title = unicode(L('More...'))
	))

####################################################################################################
def CheckError(xml):
	# See if we have any creds stored
	if not Prefs['username'] or not Prefs['password']:
		return ObjectContainer(header=unicode(L('Error')), message=unicode(L('Please enter your email and password in the preferences')))

	errorText = xml.xpath('//error/text()')
	if errorText:
		if errorText[0] == 'Access Denied':
			return ObjectContainer(header=unicode(L(errorText[0])), message=unicode(L('Please enter your correct email and password in the preferences')))
		if errorText[0] == 'Search Error':
			return ObjectContainer(header=unicode(L(errorText[0])), message=unicode(L('Search error')))
		return ObjectContainer(header=unicode(L('Error')), message=unicode(errorText[0]))

	return None

####################################################################################################
def Login():
	Log(' --> Trying to log in')
	# Dewsmen 11/13/2014:in some case get error 'OSError: Directory is not empty'
	try: 
		HTTP.ClearCache()
	except:
		Log ("Can't clear cache, please clean it manually")
	
	HTTP.ClearCookies()

	url = WATCHIS_LOGIN % (Prefs['username'], Prefs['password'])

	# Dewsmen 11/13/2014: don't need any response body on login, so change it from GET to HEAD
	#disabled cache for login 
	login = HTTP.Request(url, headers = {'Method': 'HEAD'}, cacheTime=0).headers

	# Dewsmen 11/13/2014: some OSs(found in FreeBSD) don't save cookies, so store and add them manually
	Dict['Cookie'] = {'Cookie':HTTP.CookiesForURL(WATCHIS_URL + "/api/")}

####################################################################################################
def TimeToMs(timecode):
	duration = timecode[ : -7]
	seconds = int(duration) * 60
	return seconds * 1000

