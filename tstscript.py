with open(".tmp") as tmp_file:
    for line in tmp_file.readlines():
        line = line.split("-")[1].split("Click")[0].strip()
        print(line)
