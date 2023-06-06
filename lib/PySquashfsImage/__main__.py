#!/usr/bin/env python

import argparse
import sys

from PySquashfsImage import SquashFsImage


def main():
    parser = argparse.ArgumentParser(description="Print information about squashfs images.")
    parser.add_argument("file", help="squashfs filesystem")
    parser.add_argument("paths", nargs='+', help="directories or files to print information about")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s v0.8.0")
    args = parser.parse_args()

    image = SquashFsImage(args.file)
    if len(sys.argv) > 1:
        for path in args.paths:
            print("--------------%-50.50s --------------" % path)
            squashed_file = image.root.select(path)
            if squashed_file is None:
                print("NOT FOUND")
            elif squashed_file.is_dir:
                print("FOLDER " + squashed_file.path)
                for child in squashed_file.iterdir():
                    if child.is_dir:
                        print("\t%s %-60s  <dir> " % (child.filemode, child.name))
                    elif child.is_symlink:
                        print("\t%s %s -> %s" % (child.filemode, child.name, child.readlink()))
                    else:
                        print("\t%s %-60s %8d" % (child.filemode, child.name, child.size))
            else:
                print(squashed_file.read_bytes())
    else:
        for i in image.root.find_all():
            nodetype = "FILE  "
            if i.is_dir:
                nodetype = "FOLDER"
            # print(nodetype + ' ' + i.path + " inode=" + i.inode.inode_number + " (" + image._read_block_list(i.inode) + " + " + i.inode.offset + ")")

        for i in image.root.find_all():
            if i.name.endswith(".ini"):
                content = i.read_bytes()
                print("==============%-50.50s (%8d)==============" % (i.path, len(content)))
                print(content)
            elif i.name.endswith(".so"):
                content = i.read_bytes()
                print("++++++++++++++%-50.50s (%8d)++++++++++++++" % (i.path, len(content)))
                oname = i.name + "_saved_" + str(i.inode.inode_number)
                print("written %s from %s %d" % (oname, i.name, len(content)))
                with open(oname, "wb") as of:
                    of.write(content)
        image.close()


if __name__ == "__main__":
    main()
