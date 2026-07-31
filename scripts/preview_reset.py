import sys
import datetime

from bot.models.absence import Absence

arg = sys.argv[1] if len(sys.argv) > 1 else None
if not arg:
    print('Usage: preview_reset.py MM/DD/YY or MM/DD/YYYY')
    sys.exit(2)

cutoff = None
for fm in ('%m/%d/%y','%m/%d/%Y'):
    try:
        cutoff = datetime.datetime.strptime(arg, fm)
        break
    except Exception:
        cutoff = None

if cutoff is None:
    print('INVALID_DATE')
    sys.exit(2)

count = Absence.count_before(cutoff)
print(count)
