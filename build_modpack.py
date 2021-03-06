import CONST #for 99ids
import m2modpack_tools #for scanning and json work
import re, os #parsing, scaning
from urllib.request import urlopen # for web_parsing

"""
V0.0.1 - basic parsing, making dirs and writing summary
V0.0.2 - implented asking for comment, skipping directories in scan, better {debug, printing, summary, making dirs}
V0.0.3 - implented custom_order, new function input_int(which returns some default value, if input is empty)
V0.0.4 - clearer custom_order, name_file > file_name, added moveFiles (which is a total mess), might need redesign of whole json(dict) structure
V0.0.5 - added description (another field added, which is actually comment, previous comment is the description), maybe some more improvements?
V0.0.6 - write meta file to each mod, write to csv, turn off dir_names_with_generated_numbers, get nexus_name from nexus, get desc from skyrimgems
V0.0.7 - removed custom order, making dirs with numbers, def input_int and options to run with arguments
V0.0.8 - Fallout 4 Support, getting Nexus categories
V0.0.9 - lots of rewrites, dropped making directories and summary.csv, purpose is clear now
       - to validate nexus id at lest 3 digits needs to be in file name between - chars
V0.1.0 - first usable thing, split mod_name_validator to build_modpack.py and verify_modpack.py


Verify if file is Nexus mod (by regex /\-(\d{3,})\-/) and collect info about it, do a checksum and save it as modpack_json, which can be used by others using verify_modpack.py
Currently setup for **Skyrim**, for **Fallout 4** support change Game var in Input (line 31+)

Script will scan the current directory (where the script is launched) (or change that in variable target), excluding folders and *.meta files.

TODOs
	when regex fails, try doing more strick check for IDS 01-99 or just verify files for those
	meta files for ModOrganizer loading?
	getting categories from Nexus does not work for adult content, but it works for title, fix it!
		add another option to get categories
		modify function in a way so it tries on each regex, only when categories fails, at least title will be ok
		means no skipping, just not writing categories
"""
#-------------------------------------Input-------------------------------------
Game = 'Fallout 4'
#Game = 'Skyrim'
debug = False
target = os.getcwd()
modpack_json = 'modpack.json' #output
switch_ask_for_description = False
switch_ask_for_comment = False
switch_determine_mod_install_type = True #patool needed
switch_get_nexus_info = True
if switch_get_nexus_info:
	#skyrimgems search uses nexus_name from Nexus
	#hence its not possible to do search without getting nexus info
	switch_get_skyrimgems_desc = True

#patool is needed for getting installer type
if switch_determine_mod_install_type:
	try:
		import patool_list_archives
	except ValueError as patool_missing:
		print(patool_missing)
		exit(88)
#----------------------------------- defs ------------------------------------


def validate_input():
	"""
	validates input and returns:
	game_link and game_link_replacer
	"""
	def nexus_title_replace():
		"""return string used for replacing mod page titles"""
		if Game == 'Fallout 4':
			game_link_replacer = ' at ' + Game + ' Nexus - Mods and community'
		elif Game == 'Skyrim':
			game_link_replacer = ' at ' + Game + ' Nexus - mods and community'
		return game_link_replacer

	#for FO4 no skyrimgems possible, set it global so the variable change is done
	global switch_get_skyrimgems_desc
	if Game == 'Fallout 4':
		game_link = 'fallout4'
		switch_get_skyrimgems_desc = False
	elif Game == 'Skyrim':
		game_link = 'skyrim'
	else:
		print('Game {0} is not recognized as a valid option.\nHit any key to exit.'.format(Game))
		input()
		exit(1)
	game_link_replacer = nexus_title_replace()
	return (bellow_id_100_json, game_link, game_link_replacer)





def parse_nexus_mods(mods):
	"""
	returns dict with key of the filename of the mod
	mod is full path
	mod_file_name is just file_name, used as keys in json data
	"""
	def get_nexus_info(nexus_id):
		"""
		Tries to return title and categories from nexus mods like:
		url = 'http://www.nexusmods.com/skyrim/mods/30947/'
		#TODO get author of the mod
		"""
		url = 'http://www.nexusmods.com/' + game_link + '/mods/' + nexus_id + '/'
		try: # handle if url is not reachable error
			foo = urlopen(url)
		except ValueError as url_e:
			print(url_e)
			return None
		html_source = foo.read().decode("utf-8")
        #TODO perhaps use lxml, or BS4?
		title_RE = re.compile('\<title\>(.*)\<\/title\>', re.IGNORECASE|re.DOTALL)
		categories_RE = re.compile('.*searchresults\/\?src_cat=(\d{1,3})\"\>(.*)<\/a\>')
		try:
			categories = categories_RE.search(html_source)
			title = title_RE.search(html_source).group(1)
			#fixes
			if '&#39;' in title:
				title = title.replace('&#39;','\'')
			return(
			title,
			categories.group(1),
			categories.group(2)
			)
		except AttributeError as re_e:
			#print(re_e)
			adult_RE = '\<h2\>Adult-only\scontent<\Sh2>'
			if re.search(adult_RE,html_source):
				print('\nPage {0} is for adults only and requires log-in.\
				\nPlease get nexus_name and its categories yourself.\n'.format(url))
			return (None,None,None)

	def get_skyrimgems_source():
		"""
		Retrieves html source from skyrimgems
		Used later for getting descriptions for the mods
		"""
		try: # handle if url is not reachable error
			foo = urlopen('http://www.skyrimgems.com')
		except ValueError as url_e:
			print(url_e)
			return None
		skyrimgems_source = foo.read().decode('cp852')# this just works
		return skyrimgems_source

	def search_skyrimgems_source(nexus_name): #TODO needs some filtering
		"""
		tries to match mod description with this crazy regex and then tries to do some filtering
		"""
		descriptions_RE = '.*' + nexus_name + '.*\n\s+\<td\s\w+\S+\>(.*)<\Std\>'
		try:
			fetch = re.search(descriptions_RE,skyrimgems_source).group(1)
		except AttributeError as re_e:
			if debug:
				print('"{0}" not found on Skyrim GEMS.'.format(nexus_name))
			return 'N/A'
		#TODO replace by re
		fetch.replace('[<span class="DG">DG</span>+<span class="HF">HF</span>+<span class="DB">DB</span>','[DG+HF+DB]')
		fetch.replace('[<span class="DG">DG</span>] [<span class="DB">DB</span>]', '[DG] [DB]')
		fetch.replace('[<span class="SKSE">SKSE</span>][<span class="DG">DG</span>]', '[SKSE][DG]')
		fetch.replace('[<span class="DG">DG</span> + <span class="DB">DB</span>]', '[DG+DB]')
		fetch.replace('[<span class=\"HF\">HF</span>]','[HF]')
		fetch.replace('[<span class="DB">DB</span>', '[GB]')
		fetch.replace('[<span class="DG">DG</span>]','[DG]')
		fetch.replace('[<span class=\"SKSE\">SKSE</span>]','[SKSE]')
		return fetch

	def load_bellow_id_100_data(Game):
		"""
		returns dict of nexus ids bellow 100

        should be called only once
		"""
        if Game == 'Fallout 4':
    		return CONST.fallout4_99_ids
    	elif Game == 'Skyrim':
    		return CONST.skyrim_99_ids

	def search_in_bellow_id_100_data(target, data):
		"""
		goes through data, which are specific structure
		for nexus ids bellow 100 based in list of file_names(data[i][0])

		returns id of the mod(the key of data)
		"""
		for i in data.keys():
			if not data[i][0] == None:
				if any(target in file_name for file_name in data[i][0]):
					#print the whole value of the key except the first mod_filename_list
					##print(data[i][1:])
					return i

	d = {}
	failed = []
	re_nexus_id = r'\-(\d{3,})\-?' #- at least theree digits and optionaly -
	bellow_id_100_data = None #load only if something fails regex

	#if geting info from Skyrim GEMS, load the page source
	if switch_get_nexus_info and switch_get_skyrimgems_desc:
		skyrimgems_source = get_skyrimgems_source()

	for mod in mods:
		mod_file_name = mod[mod.rfind('\\') + 1:]
		#---------------------- get_name_nexus_id_version ----------------------
		extension = mod_file_name[mod_file_name.rfind('.'):]
		#TODO few more tries?
		try:
			nexus_id = re.search(re_nexus_id, mod_file_name).group(1)
		except AttributeError as re_error_nexus_id:
			print('\nWARNING: Item "{0}" has probably ID bellow 100, trying to check for ids...\n'.format(mod_file_name))
			#try looking if the file_name has nexus_id bellow 100
			if not bellow_id_100_data:
				bellow_id_100_data = load_bellow_id_100_data(Game)
			nexus_id = search_in_bellow_id_100_data(mod_file_name, bellow_id_100_data)
			#if failed then skip, the file is surely not for nexus
			if not nexus_id:
				print('\nERROR: For item "{0}" regex failed, skipping\n'.format(mod_file_name))
				failed.append(mod_file_name)
				continue
		re_name_version = re.compile('(.*)-' + nexus_id + '-?(.*)' + extension)
		if debug:
			print('Using re {0} on {1}'.format(re_name_version.pattern, mod_file_name))
		try:
			name = re_name_version.search(mod_file_name).group(1)
		except AttributeError as re_error_mod_name:
			#todo handle cases without no Name
			name = None
		try:
			version = re.search(re_name_version, mod_file_name).group(2)
		except AttributeError as re_error_mod_version:
			version = 'N\A'
		#--------------------------- get_nexus_info ----------------------------
		if switch_get_nexus_info:
			(nexus_name, nexus_modCategoryN, nexus_modCategory) = get_nexus_info(nexus_id)
			if nexus_name:
				nexus_name = nexus_name.replace(game_link_replacer,'')
			else:
				print('\nFailed to get info from nexusmods.com for {0}\n'.format(name))
				nexus_name, nexus_modCategoryN, nexus_modCategory = None, None, None
		#------------------------------ save info ------------------------------
		d[mod_file_name] = {}
		d[mod_file_name]['name'] = name
		d[mod_file_name]['file_name'] = name + '-' + nexus_id + '-' + version + extension
		d[mod_file_name]['sha1'] = m2modpack_tools.make_checksum(mod)
		d[mod_file_name]['modID'] = nexus_id
		d[mod_file_name]['nexus_link'] = 'http://www.nexusmods.com/' + game_link + '/mods/' + nexus_id + '/'
		d[mod_file_name]['version'] = version
		if switch_get_nexus_info:
			d[mod_file_name]['nexus_name'] = nexus_name
			d[mod_file_name]['nexus_categoryN'] = nexus_modCategoryN
			d[mod_file_name]['nexus_category'] = nexus_modCategory
			if switch_get_skyrimgems_desc and nexus_name is not None:
				d[mod_file_name]['skyrimgems_desc'] = search_skyrimgems_source(nexus_name)
		#custom input
		if switch_ask_for_description:
			d[mod_file_name]['description'] = input('Insert your description: ')
		if switch_ask_for_comment:
			d[mod_file_name]['comment'] = input('Insert your comment: ')
		if switch_determine_mod_install_type:
			#check if mod has FOmod\\ModuleConfig.xml - installer
			d[mod_file_name]['has_installer'] = patool_list_archives.Archive(mod)\
								.search_for_file_in_archive(r'FOMod\\\\ModuleConfig.xml')
		#----------------------------- print info ------------------------------
		if switch_get_nexus_info:
			if version == 'N\A':
				print('\nValidated {0}\nName:{1}\nID:{2}\nCategory:{3}\nInstaller:{4}'.format(mod_file_name, name, nexus_id, nexus_modCategory, d[mod_file_name]['has_installer']))
			else:
				print('\nValidated {0}\nName:{1}\nID:{2}\nV:{3}\nCategory:{4}\nInstaller:{5}'.format(mod_file_name, name, nexus_id, version, nexus_modCategory, d[mod_file_name]['has_installer']))
		else:
			if version == 'N\A':
				print('\nValidated {0}\nName:{1}\nID:{2}\nInstaller:{3}'.format(mod_file_name, name, nexus_id, d[mod_file_name]['has_installer']))
			else:
				print('\nValidated {0}\nName:{1}\nID:{2}\nV:{3}\nInstaller:{4}'.format(mod_file_name, name, nexus_id, version, d[mod_file_name]['has_installer']))
		if debug:
			print('file_name:', mod_file_name)
			print('file_name exists?', os.path.exists(mod))
			print('name:', name)
			print('nexus_id:', nexus_id)
			print('version:', version)
			print('extension:', extension)
			print('constructed_file_name:', name + '-' + nexus_id + '-' + version + extension)
			if switch_get_nexus_info:
				print('nexus_name:', nexus_name)
				print('nexus_categoryN:', nexus_modCategoryN)
				print('nexus_category:', nexus_modCategory)
	#--------------------------------finalize-----------------------------------
	if debug:
		print('These mods failed to get parsed:', failed)
	return d


#-----------------------------------------------------------------------------
if __name__ == "__main__":
	bellow_id_100_json, game_link, game_link_replacer = validate_input() #exit if not OK
	#-----------------------------scan current dir------------------------------
	mods_list = m2modpack_tools.scan_dir(target)
	#-------------------------------- get info ---------------------------------
	print('Building modpack from all mod files in', target)
	mods_data = parse_nexus_mods(mods_list)
	#------------------------------- save json ---------------------------------
	if len(mods_data) != 0: #some mod found
		m2modpack_tools.try_save_json(modpack_json, mods_data)
