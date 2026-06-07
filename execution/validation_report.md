# Galaxy vs v2-native pggb validation

- galaxy_gfa: `/home/anton/git/pangenome_tools_wfs/execution/outputs/v2replicate.smooth.final.gfa.gz`
- v2_gfa:     `/home/anton/git/Pv4-pangenome/v2/pggb_out/pggb_input.fa.gz.f705205.c28ecf8.dcad0e6.smooth.fix.gfa.gz`

## GFA line counts
| tag | galaxy | v2 | diff %% |
|----:|-------:|---:|-------:|
| H | 1 | 1 | +0.000 |
| L | 1961474 | 4359267 | -55.004 |
| P | 1328 | 1318 | +0.759 |
| S | 1432361 | 3127438 | -54.200 |

**S/L/P counts within +-0.5%%: False**

## Canonical GFA md5
- galaxy: `d9fe683dfe2adef70098f9e683c1907b`
- v2:     `676ecf85856e69e6dbd7a68b046b4b22`
- match:  **False**

## odgi stats (built from GFA)
| metric | galaxy | v2 | diff %% |
|--------|-------:|---:|-------:|
| #length | 67138937 | 57166984 | +17.444 |
| nodes | 1432361 | 3127438 | -54.200 |
| edges | 1961474 | 4359267 | -55.004 |
| paths | 1328 | 1318 | +0.759 |
| steps | 7018903 | 16257529 | -56.827 |

**odgi stats within +-0.5%%: False**