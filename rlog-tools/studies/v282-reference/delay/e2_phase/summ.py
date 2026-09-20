import json, glob, sys
for fn in sorted(glob.glob('out/real_*.json')):
    d = json.load(open(fn)); print(d['route'], 'handsoff s', round(d['handsoff_s']), 'chunks', d['n_chunks'])
    for b in ['v0-8', 'v8-15', 'v15-99']:
        x = d[b]; line = f"  {b} n{x['n_chunks']:3d}"
        for k in ['direct_rate', 'iv_rate', 'direct_angle', 'iv_angle', 'direct_joint', 'iv_joint']:
            y = x.get(k)
            if y and y.get('fit'):
                ci = y.get('D_boot_ci95'); ft = y['fit']
                line += f" | {k} {ft['D']*1e3:.0f}[{ci[0]*1e3:.0f},{ci[1]*1e3:.0f}]" if ci else f" | {k} {ft['D']*1e3:.0f}[-]"
                line += f" J{ft['J']:.0e} nb{ft['nbins']}"
            else:
                line += f" | {k} --"
        print(line)
