import curses, locale, multiprocessing, subprocess, shlex, time, os; 

def sorter(filepath, s_type, running_dir):
    temp1_list = os.listdir(filepath);
    temp2_list = [];
    for x in temp1_list:
        if (x[-4:] in [".mp3", ".wav", "ogg", ".oga", ".m4a", ".aac", "flac"]): #this won't work if I want to put in folders and "../"
            temp2_list.append(x);
    if(s_type == "a-z"): #sorting
        temp2_list.sort();
    if(s_type == "z-a"):
        temp2_list.sort(reverse=True);
    if(s_type == "size"):
        os.chdir(filepath); #change cwd so os.path works
        temp2_list.sort(key=os.path.getsize);
        os.chdir(running_dir); #reset to dir file is running in
    if(s_type == "size_rev"):
        os.chdir(filepath); #change cwd so os.path works
        temp2_list.sort(reverse=True, key=os.path.getsize);
        os.chdir(running_dir); #reset to dir file is running in
    if(s_type == "date"):
        os.chdir(filepath);
        temp2_list.sort(key=os.path.getmtime);
        os.chdir(running_dir);
    if(s_type == "date_rev"):
        os.chdir(filepath);
        temp2_list.sort(reverse=True, key=os.path.getmtime);
        os.chdir(running_dir);
    return temp2_list;

##############################

def show_list(current_dir, sort_types, sort_mode, song_list, song_pad, running_dir): #actual drawing of list of songs on pad
    #song_list = sorter(current_dir, sort_types[sort_mode], running_dir);
    for i in range(0,len(song_list)):
        song_pad.addstr(i,0,song_list[i]);
    pass;

##############################

def write_play_state(state, scr): #TODO: make this change the values of playing and stopped vars. should there be paused var?
    if(state == "Playing"):
        scr.addstr(term_h-3,5,"Playing",curses.A_UNDERLINE|curses.A_ITALIC|curses.color_pair(1));
    if(state == "Stopped"):
        scr.addstr(term_h-2,1,chr(32)*70); #clear now playing
        scr.addstr(term_h-3,5,"Stopped",curses.A_UNDERLINE|curses.A_ITALIC|curses.color_pair(2));
    if(state == "Paused "):
        scr.addstr(term_h-3,5,"Paused ",curses.A_UNDERLINE|curses.A_ITALIC|curses.color_pair(3));

##############################

def main(stdscr):
    #curse intialization
    curses.start_color();
    curses.use_default_colors();
    curses.init_pair(1,curses.COLOR_BLUE,-1); #play
    curses.init_pair(2,curses.COLOR_RED,-1); #stop
    curses.init_pair(3,curses.COLOR_YELLOW,-1); #pause
    curses.curs_set(0);
    #curses.mouseinterval(200);
    global term_h, term_w; #the value of these should never change once set
    term_h, term_w = stdscr.getmaxyx();
    stdscr.nodelay(True);
    stdscr.keypad(True);
    stdscr.box();
    stdscr.refresh();
    
    #songs initialization
    running_dir = os.getcwd();
    current_dir = open("/home/yobleck/.moc/last_directory","r").readline(); #TODO: make this navigable without opening mocp
    sort_types = ["date_rev", "date",  "size", "size_rev", "a-z", "z-a"];
    sort_mode = 0; #TODO: set initial sort mode from ini file
    stdscr.addstr(term_h-3,term_w-20,"sort mode: " + sort_types[sort_mode],curses.A_UNDERLINE|curses.A_ITALIC);
    
    
    #pad where list of songs is shown to the user
    song_pad = curses.newpad(len(os.listdir(current_dir)),100); #this assumes no file names over 100 char TODO: work after song added or removed
    top_of_pad = 0;
    
    #initial sorting and showing of songs
    song_list = sorter(current_dir, sort_types[sort_mode], running_dir);
    show_list(current_dir, sort_types, sort_mode, song_list, song_pad, running_dir);
    
    #highlighting song to be selected
    highlighted_song = 0;
    selected_song = None; #not being used
    if(subprocess.run(["mocp", "-i"],stdout=subprocess.PIPE,stderr=open(os.devnull, 'w')).stdout[0:11] == b'State: PLAY'):
        playing = True; #if song is already playing on server when mocs is opened
        stopped = False;
        write_play_state("Playing",stdscr);
    else:
        playing = False;
        stopped = True;
        write_play_state("Stopped",stdscr);
    
    song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE); #this is messed up by chars > 1 width
    song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-4,term_w-2);
    
    #autoplay next song
    autoplay = True; #TODO:read from ini file later
    stdscr.addstr(term_h-3,15,"Autoplay",curses.color_pair(1));
    
    temp = None; #holds server status
    loop_count = 1; #for checking if song is finished
    running = True;
    while(running):
        usr_input = stdscr.getch(); #get user input
        
        if(usr_input != -1): #show key press
            stdscr.addstr(term_h-3,1,"    "); #clears screen
            stdscr.addstr(term_h-3,1,str(usr_input));
        
        if(usr_input == 27): #esc close program
            running = False;
        
        
        if(usr_input == 10): #enter start playing
            playing = True;
            stopped = False;
            subprocess.run(["mocp", "-l", current_dir + "/" + song_list[highlighted_song]]);
            temp = None; #stops autoplay from skipping selected song
            stdscr.addstr(term_h-2,1,chr(32)*70); #clear TODO: doesnt work properly with extra width chars
            stdscr.addstr(term_h-2,1,str(song_list[highlighted_song])[:70],curses.color_pair(1)); #show mow playing on screen TODO: get info from mocp -i
            write_play_state("Playing",stdscr);
        
        if(usr_input == 97): # a toggle autoplay
            if(autoplay):
                autoplay = False;
                stdscr.addstr(term_h-3,15,"Autoplay",curses.color_pair(2));
            else:
                autoplay = True;
                stdscr.addstr(term_h-3,15,"Autoplay",curses.color_pair(1));
        
        #Autoplay    TODO: fix scroll wheel issue
                     #what should this number be to minimize lag while not having a long pause between songs?
        if(loop_count%200 == 0 and playing and not stopped and usr_input != 10):
            loop_count = 0;
            temp = subprocess.run(["mocp", "-i"],stdout=subprocess.PIPE,stderr=open(os.devnull, 'w')).stdout; #get server status
            
            if(autoplay):
                if(temp == b'State: STOP\n'): #check if song playing
                    if(highlighted_song < len(song_list)-1): #this is just copy and pasted from down arrow key
                        song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_NORMAL);
                        highlighted_song += 1;
                        song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE);
                        if(highlighted_song >= top_of_pad + term_h-4):
                            top_of_pad += 1;
                        song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-4,term_w-2);
                        time.sleep(.4); #can't connect to server error without this
                        subprocess.run(["mocp", "-l", current_dir + "/" + song_list[highlighted_song]]);
                        stdscr.addstr(term_h-2,1,chr(32)*70);
                        stdscr.addstr(term_h-2,1,str(song_list[highlighted_song])[:70],curses.color_pair(1));
                        temp = None; #resets server status
                    else:
                        playing = False; #should stopped = True here? or will that break pause behavior
                        stopped = True;
                        write_play_state("Stopped",stdscr);
            else:
                if(temp == b'State: STOP\n'):
                    playing = False;
                    stopped = True;
                    write_play_state("Stopped",stdscr);
                    
        loop_count += 1;
        
        #TODO: next and provious song. maybe package autoplay into a function and call that
        #TODO: volume control through mocp -v (+/-)number
        #TODO: build shuffle, autonext, repeat into autoplay?
        
        if(usr_input == 32): #space play/pause TODO: simplify by running mocp --toggle-pause?
            if(not playing):
                if(not stopped):
                    playing = True;
                    subprocess.run(["mocp", "-U"]); #unpause
                    write_play_state("Playing",stdscr);
            else:
                if(not stopped):
                    playing = False;
                    subprocess.run(["mocp", "-P"]); #pause
                    write_play_state("Paused ",stdscr);
        
        if(usr_input == 115): #s stop
            playing = False;
            stopped = True;
            subprocess.run(["mocp", "-s"]);
            write_play_state("Stopped",stdscr);
        
        
        if(usr_input == 259): #w up
            if(highlighted_song > 0):
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_NORMAL);
                highlighted_song -= 1;
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE);
                if(highlighted_song < top_of_pad):
                    top_of_pad -= 1;
                song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-4,term_w-2);
                
        if(usr_input == 258): #s down
            if(highlighted_song < len(song_list)-1):
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_NORMAL);
                highlighted_song += 1;
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE);
                if(highlighted_song >= top_of_pad + term_h-4):
                    top_of_pad += 1;
                song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-4,term_w-2);
        
        
        if(usr_input == 260): #song seeking
            subprocess.run(["mocp", "-k", "-1"]);
        if(usr_input == 261):
            subprocess.run(["mocp", "-k", "1"]);
        
        
        if(usr_input == 109): #m switch sort modes
            if(sort_mode < len(sort_types)-1):
                sort_mode += 1;
            else:
                sort_mode = 0;
            song_list = sorter(current_dir, sort_types[sort_mode], running_dir); #resorts list
            song_pad.clear();
            show_list(current_dir, sort_types, sort_mode, song_list, song_pad, running_dir); #redraw list on screen
            top_of_pad = 0; #reset to top of screen
            highlighted_song = 0;
            song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE);
            song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-4,term_w-2);
            stdscr.addstr(term_h-3,term_w-9,"        "); #redraw sort mode on screen
            stdscr.addstr(term_h-3,term_w-20,"sort mode: " + sort_types[sort_mode],curses.A_UNDERLINE|curses.A_ITALIC);
            
    
        time.sleep(.01); #reduce cpu usage and stop loop from spamming?
    #end while loop
#end main

locale.setlocale(locale.LC_ALL, '')
os.environ.setdefault('ESCDELAY', '25') #why do I not need this in gtav_radio.py?
curses.wrapper(main);
