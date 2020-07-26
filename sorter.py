import curses, locale, multiprocessing, subprocess, shlex, time, os; 
#TODO: add now playing (how should this interact with changing sort mode?), fix scroll wheel issue

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

def show_list(current_dir, sort_types, sort_mode, song_list, song_pad, running_dir): #actual drawing of list of songs on pad
    song_list = sorter(current_dir, sort_types[sort_mode], running_dir);
    for i in range(0,len(song_list)):
        song_pad.addstr(i,0,song_list[i]);
    pass;


def main(stdscr):
    #curse intialization
    curses.use_default_colors();
    curses.curs_set(0);
    #curses.mouseinterval(200);
    term_h, term_w = stdscr.getmaxyx();
    stdscr.nodelay(True);
    stdscr.box();
    stdscr.refresh();
    
    #songs initialization
    running_dir = os.getcwd();
    current_dir = open("/home/yobleck/.moc/last_directory","r").readline(); #TODO: make this navigable without opening mocp
    sort_types = ["date_rev", "date",  "size", "size_rev", "a-z", "z-a"];
    sort_mode = 0;
    stdscr.addstr(term_h-2,term_w-20,"sort mode: " + sort_types[sort_mode]);
    stdscr.addstr(term_h-2,term_w-30,"Stopped");
    
    #pad where list of songs is shown to the user
    song_pad = curses.newpad(len(os.listdir(current_dir)),100); #this assumes no file names over 100 char
    top_of_pad = 0;
    
    #initial sorting and showing of songs
    song_list = sorter(current_dir, sort_types[sort_mode], running_dir);
    show_list(current_dir, sort_types, sort_mode, song_list, song_pad, running_dir);
    
    #highlighting song to be selected
    highlighted_song = 0;
    selected_song = None; #not being used
    playing = False;
    stopped = True;
    song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE); #this is screwed up by jp chars greater than 1 width
    song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-3,term_w-2);
    
    #autoplay next song
    autoplay = True; #TODO:read from file later
    
    temp = None;
    running = True;
    while(running):
        usr_input = stdscr.getch(); #get user input
        
        if(usr_input != -1): #show key press
            stdscr.addstr(term_h-2,1,"    ");
            stdscr.addstr(term_h-2,1,str(usr_input));
        
        if(usr_input == 27): #esc close program
            running = False;
        
        
        if(usr_input == 10): #enter start playing
            playing = True;
            stopped = False;
            subprocess.run(["mocp", "-l", current_dir + "/" + song_list[highlighted_song]]);
            stdscr.addstr(term_h-2,term_w-30,"Playing");
            
        #autoplay
        #""" #sorta works but cant connect to server error. WHATS CAUSING IT?!?!?!?
        temp = subprocess.run(["mocp", "-i"],stdout=subprocess.PIPE,stderr=open(os.devnull, 'w')).stdout;
        if(autoplay and playing and usr_input != 10 and not stopped and temp == b'State: STOP\n'): #checks if song playing
            if(highlighted_song < len(song_list)-1): #this is just copy and pasted from down arrow key
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_NORMAL);
                highlighted_song += 1;
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE);
                if(highlighted_song >= top_of_pad + term_h-3):
                    top_of_pad += 1;
                song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-3,term_w-3);
                time.sleep(.5); #can't connect to server error without this
                subprocess.run(["mocp", "-l", current_dir + "/" + song_list[highlighted_song]]);
            else:
                playing = False;
            #"""
            
        
        if(usr_input == 32): #space play/pause
            if(not playing):
                if(not stopped):
                    playing = True;
                    subprocess.run(["mocp", "-U"]); #unpause
                    stdscr.addstr(term_h-2,term_w-30,"Playing");
            else:
                if(not stopped):
                    playing = False;
                    subprocess.run(["mocp", "-P"]); #pause
                    stdscr.addstr(term_h-2,term_w-30,"Paused ");
        
        if(usr_input == 115): #s stop
            playing = False;
            stopped = True;
            subprocess.run(["mocp", "-s"]);
            stdscr.addstr(term_h-2,term_w-30,"Stopped");
        
        
        if(usr_input == 259): #w up
            if(highlighted_song > 0):
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_NORMAL);
                highlighted_song -= 1;
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE);
                if(highlighted_song < top_of_pad):
                    top_of_pad -= 1;
                song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-3,term_w-2);
                
        if(usr_input == 258): #s down
            if(highlighted_song < len(song_list)-1):
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_NORMAL);
                highlighted_song += 1;
                song_pad.chgat(highlighted_song,0,min(len(song_list[highlighted_song]), term_w-2),curses.A_REVERSE);
                if(highlighted_song >= top_of_pad + term_h-3):
                    top_of_pad += 1;
                song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-3,term_w-2);
        
        
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
            song_pad.refresh(top_of_pad,0 ,1,1 ,term_h-3,term_w-2);
            stdscr.addstr(term_h-2,term_w-9,"        "); #redraw sort mode on screen
            stdscr.addstr(term_h-2,term_w-20,"sort mode: " + sort_types[sort_mode]);
            
    
        #time.sleep(.01); #reduce cpu usage and stop loop from spamming?
    #end while loop
#end main

locale.setlocale(locale.LC_ALL, '')
os.environ.setdefault('ESCDELAY', '25') #why do I not need this in gtav_radio.py?
curses.wrapper(main);
