import math, time, sys;

#timer function
def timer_bar(duration, bar_length=20, progress_sym="#", remainder_sym=" ", new_line=True, prnt=True): #https://pynative.com/python-range-for-float-numbers/
    if(prnt): #print to screen
        if(new_line):
            print();
        step = float(duration)/bar_length;
        for i in range(0,bar_length): #need the +1?
            print("\033[F\33[2K" + "[" + progress_sym*i + remainder_sym*(bar_length - i) + "]"); #print i/bar_length percent complete?
            time.sleep(step);
        print("\033[F\33[2K" + "[" + progress_sym*bar_length + "]"); #this line is annoying but cant think of a way to cram x states into x-1 steps
        print("done");
    else: #return as string
        return "WIP (may not be feasible)";

#progress bar
#takes percentages between 0 and 1 as input
#remember to print a newline buffer before calling this function for the first time with new_line=True
def progress_bar(percentage, bar_length=20, progress_sym="#", remainder_sym=" ", new_line=False, prnt=True):
    if(prnt): #print to screen
        if(new_line):
            print();
        print("\033[F\33[2K" + 
            "[" + progress_sym*math.floor(percentage*bar_length) + 
            remainder_sym*(bar_length - math.floor(percentage*bar_length)) + "]");
    else: #return as string
        return "[" + progress_sym*math.floor(percentage*bar_length) + remainder_sym*(bar_length - math.floor(percentage*bar_length)) + "]";

#TODO: import module that allows special ANSI characters to work on windows

#first argument after file name is t for timer or p for percentage bar. second argument is the duration of timer or percentage respectively
if __name__ == "__main__":
    if(len(sys.argv) > 1):
        if(sys.argv[1] == "t"):
            timer_bar(sys.argv[2]);
        if(sys.argv[1] == "p"):
            progress_bar(sys.argv[2]);
    #globals()[sys.argv[1]](sys.argv[2]);
