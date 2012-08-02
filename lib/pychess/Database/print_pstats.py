import pstats

p=pstats.Stats('rep.prof')
p.sort_stats('cumulative')
p.print_stats(60)
