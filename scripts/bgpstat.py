import bgpstat_inc as bgpstat
import curses
from curses.textpad import Textbox, rectangle
import locale
import argparse
import socket
from datetime import datetime, timedelta

# Force a locale that can handle line drawing characters
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# Set initial watch delay
delay = 2

# Get the hostname for the title bar
hostname = socket.gethostname()

# Create dict to match keywords to colors (ansi escape codes for single run)
color_rules_ansi = {
  "ASN": "\x1b[36;1m", # bold cyan
  "Established": "\x1b[32;1m", # bold green
  "Connect": "\x1b[33;1m", # bold yellow
  "Idle": "\x1b[33;1m", # bold yellow
  "OpenSent": "\x1b[33;1m", # bold yellow
  "OpenConfirm": "\x1b[33;1m", # bold yellow
  "Active": "\x1b[31;1m", # bold red
  "Up": "\x1b[32;1m", # bold green
  "Down": "\x1b[31;1m", # bold red
  "*DEFAULT*": "\x1b[0m"
}

### ANSI color codes  \x1b[#;#;#m
### Foreground - Background = Color         Decorators
# 30 - 40 = Black                           0 = Reset
# 31 - 41 = Red                             1 = Bold
# 32 - 42 = Green                           4 = Underline
# 33 - 43 = Yellow                          7 = Reverse
# 34 - 44 = Blue
# 35 - 45 = Magenta
# 36 - 46 = Cyan
# 37 - 47 = White

# Returns a value making sure it's inside the defined boundaries
def setIntBounds(newValue, lowerBound, upperBound):
  if newValue < lowerBound:
    newValue = lowerBound
  if newValue > upperBound:
    newValue = upperBound
  return newValue


# Shortcut wrapper for datetime.now()
def now():
  return datetime.now()


# Parses line and inserts curses colors based on keywords
def printToPad(win, y, x, text, color_rules):
  win.move(y, x)
  textsplit = text.split(" ")

  for i in range(0, len(textsplit)):
    if textsplit[i] in color_rules:
      win.addstr(textsplit[i], color_rules[textsplit[i]])
    else:
      win.addstr(textsplit[i])
    if i < len(textsplit):
      win.addstr(" ") # there are more words so add a space to the end before continuing the loop


# Parses line and inserts curses colors based on keywords
def printToCons(text, color_rules):
  textsplit = text.split(" ")

  for i in range(0, len(textsplit)):
    if textsplit[i] in color_rules:
      colorStart = color_rules[textsplit[i]]
      colorEnd = color_rules["*DEFAULT*"]
      textsplit[i] = f"{colorStart}{textsplit[i]}{colorEnd}"
  print(" ".join(textsplit))


# Make the enter key terminate the textbox
def textbox_validator(x):
  if x == 10:
    x = 7
  return x


def curses_app(stdscr):
  # Create color pairs
  curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
  curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
  curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
  curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
  curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
  BOLD = curses.color_pair(1) | curses.A_BOLD
  GOOD = curses.color_pair(2) | curses.A_BOLD
  WARN = curses.color_pair(3) | curses.A_BOLD
  BAD = curses.color_pair(4) | curses.A_BOLD
  HEADER_FOOTER = curses.color_pair(5)

  # Create dict to match keywords to colors
  color_rules_curses = {
    "ASN": BOLD,
    "Established": GOOD,
    "Connect": WARN,
    "Idle": WARN,
    "OpenSent": WARN,
    "OpenConfirm": WARN,
    "Active": BAD,
    "Up": GOOD,
    "Down": BAD
  }

  # Filter variable init
  extraText = ""
  filterText = ""

  # Some initial screen setup
  stdscr.erase()
  curses.curs_set(0)  # Disable the cursor
  stdscr.idcok(False)  # Reduce screen flicker
  stdscr.idlok(False)  # Reduce screen flicker
  stdscr.refresh()

  # Create the pad that will hold the main content
  pad = curses.newpad(500, 500) 

  # Variable init
  key = 0
  cursorTop = 0
  cursorLeft = 0
  padHeight = 0
  padWidth = 0
  lastBGP = now() - timedelta(seconds = delay+1)

  stdscr.nodelay(True)  # don't wait for keyboard input (non-blocking)

  # start the loop - keep checking for user input and keep the screen refreshed
  # loop until user presses q or Q
  while key not in [ord('q'), ord('Q')]:
    # Refresh screen size in case of resize
    scrLines, scrCols = stdscr.getmaxyx()

    try:
      timeText = f'{now().strftime("%-I:%M:%S%p").lower()[:-1]} '
      hostText = f' BGP status for {hostname}'
      titleSpacer = " " * (scrCols - len(hostText) - len(timeText))
      titleText = f'{hostText}{titleSpacer}{timeText}'
      stdscr.addstr(0, 0, titleText, HEADER_FOOTER)

      # Bug workaround to fix crash when attempting to addstr or addch in the bottom right corner of the screen
      botLeftText = " Q=Quit | F=Filter "
      refreshText = f"Delay: {delay}s "
      footerSpacer = " " * (scrCols - len(botLeftText) - len(extraText) - len(refreshText) - 1) # Insert 1 less space than necessary to fill the width
      footerText = f'{botLeftText}{extraText}{footerSpacer}{refreshText}'
      stdscr.addstr(scrLines-1, 0, footerText, HEADER_FOOTER)
      stdscr.insch(scrLines-1, len(footerText)-len(refreshText), " ", HEADER_FOOTER) # Insert 1 space to the left of the bottom right element
    except:
      pass
    stdscr.refresh()
    
    # Wait for the delay to elapse before updating the bgp status
    if (now() - lastBGP).total_seconds() > delay:
      # update status and timestamp
      bgpstatus = '\n' + bgpstat.get_bgp_status(filterText)
      lastBGP = now()

      # erase the pad and refresh with updated content
      pad.erase()
      padline = 0
      for bgpline in bgpstatus.splitlines():
        printToPad(pad, padline, 0, bgpline, color_rules_curses)
        padline += 1
        padHeight = padline
        padWidth = max(padWidth, len(bgpline))

      # restore the cursor position inside the pad
      pad.move(cursorTop, cursorLeft)

    try:
      # this is in a try/except to catch errors caused by the screen being resized too small
      pad.refresh(cursorTop, cursorLeft, 1, 0, scrLines-2, scrCols-1)
    except:
      pass

    # get keyboard input
    try:
      # a key was pressed
      key = stdscr.getch()
    except:
      # no key was pressed
      key = 0
    
    # check keyboard input
    if key == curses.KEY_DOWN:
      cursorTop = setIntBounds(cursorTop+1, 0, padHeight-2)
    elif key == curses.KEY_UP:
      cursorTop = setIntBounds(cursorTop-1, 0, padHeight-2)
    elif key == curses.KEY_RIGHT:
      cursorLeft = setIntBounds(cursorLeft+5, 0, padWidth-1)
    elif key == curses.KEY_LEFT:
      cursorLeft = setIntBounds(cursorLeft-5, 0, padWidth-1)
    elif key == curses.KEY_NPAGE:
      cursorTop = setIntBounds(cursorTop+scrLines-2, 0, padHeight-2)
    elif key == curses.KEY_PPAGE:
      cursorTop = setIntBounds(cursorTop-scrLines-2, 0, padHeight-2)
    elif key == curses.KEY_HOME:
      cursorLeft = 0
    elif key == curses.KEY_END:
      cursorLeft = padWidth-1
    elif key == curses.KEY_RESIZE:
      scrLines, scrCols = stdscr.getmaxyx()
      try:
        # clear the line before last to clear up artifacts left by rapidly resizing
        stdscr.addstr(scrLines-1, 0, " "*scrCols)
      except:
        # continue silently
        pass
    elif key in [ord('f'), ord('F')]:
      try:
        # Setup filter window display
        tbTop = scrLines - 2
        tbLeft = 2
        tbHeight = 1
        tbWidth = scrCols - 4
        # Paint the window
        textwin = curses.newwin(tbHeight, tbWidth, tbTop, tbLeft)
        rectangle(stdscr, tbTop-1, tbLeft-1, tbTop+tbHeight, tbLeft+tbWidth)
        stdscr.addstr(tbTop-1, tbLeft, " Filter: ")
        # Insert the textbox inside the border
        textbox = Textbox(textwin)
        # Redraw the screen with the text window
        stdscr.refresh()
        # Enable the cursor
        curses.curs_set(1)
        # Start getting user input
        textbox.edit(textbox_validator)
        # Get and strip input from the textbox
        filterText = textbox.gather().strip()
        if filterText:
          extraText = f'[{filterText}]'
        else:
          extraText = ''
        # Disable the cursor
        curses.curs_set(0)
        # Erase and redraw the screen to get rid of the filter window
        stdscr.erase()
        stdscr.refresh()
      except:
        # Silently ignore errors, usually caused by screen resizing
        pass


if __name__ == "__main__":
  ### Init argparse
  parser = argparse.ArgumentParser(description='Display BGP peer status')
  parser.add_argument('-w', '--watch', dest='watch', action='store_true', required=False, help='Keep updating the status, refreshing every so many seconds')
  parser.add_argument('-d', '--delay', dest='delay', type=int, default=2, required=False, metavar='n', help='Seconds to wait between updates (default=2)')
  args = parser.parse_args()
  
  if args.watch:
    # -w was given so start up the curses wrapper
    delay = args.delay
    curses.wrapper(curses_app)
  else:
    # running one-shot so manually print the status with ANSI colors and exit
    for line in bgpstat.get_bgp_status().splitlines():
      printToCons(line, color_rules_ansi)
