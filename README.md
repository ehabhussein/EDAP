For a more cleaner README and usage examples

https://raw.githubusercontent.com/ehabhussein/EDAP/master/raw_readme

Consider using the pypy interpreter over than the normal python interpreter for optimising speed.
http://pypy.org

Mac:
sudo port install pypy

 Usages:
 
$ pypy EDAP.py input-file.txt <number of generated hashes> random   [truly random based on charset , length , chars found] [unstrict]

$ pypy EDAP.py input-file.txt <number of generated hashes> smart    [based on input , weight & positions] [strict]

$ pypy EDAP.py input-file.txt <number of generated hashes> patterns [based on smart + char cases] [very strict]
        
        
        
------------------------------------------------------------------------

$ time pypy EDAP.py ../OhHaithere/urls.txt 1000 random
real    0m0.338s
user    0m0.293s
sys    0m0.039s

$ time python EDAP.py ../OhHaithere/urls.txt 1000 random
real    0m0.099s
user    0m0.081s
sys    0m0.016s



----------------------------------

$ time pypy EDAP.py ../OhHaithere/urls.txt 1000 smart
real    0m6.235s
user    0m6.116s
sys    0m0.113s

$ time python EDAP.py ../OhHaithere/urls.txt 1000 smart
real    0m20.749s
user    0m20.628s
sys    0m0.118s


------------------------------------



$ time python EDAP.py ../OhHaithere/urls.txt 1000 patterns
real    0m22.386s
user    0m22.221s
sys    0m0.160s

$ time pypy EDAP.py ../OhHaithere/urls.txt 1000 patterns
real    0m6.437s
user    0m6.325s
sys    0m0.104s


