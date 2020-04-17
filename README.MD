## How to run



```
git clone https://github.com/raunaqness/master-and-racers.git
cd master-and-racers
```

Build Docker Images

```
sh build.sh
```

Run 

- You can set the numbers of racers using the `--scale` flag

```
docker-compose up --scale racer=5
```

Input

Input file for Master process is `data/input.txt` where each line is space-separated value of 'm' (slope) and 'c' (constant) for racers.
If number of Racer processes are more than line in `input.txt`, values get read from the beginning (like circular queue). 

Made by Raunaq