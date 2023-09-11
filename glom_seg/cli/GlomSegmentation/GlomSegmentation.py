import os
import sys
from ctk_cli import CLIArgumentParser


def main(args):  
    cwd = os.getcwd()
    print(cwd)
    os.chdir(cwd)

    cmd = "python3 ../glom_code/test.py   --basedir {}  --non_gs_model {} --gs_model {} --girderApiUrl {} \
                --girderToken {} --input_files {}".format(args.base_dir, args.non_gs_model, args.gs_model, args.girderApiUrl, args.girderToken, args.input_files)
    print(cmd)
    sys.stdout.flush()
    os.system(cmd)  


if __name__ == "__main__":
    main(CLIArgumentParser().parse_args())