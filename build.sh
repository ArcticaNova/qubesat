# $1 is driver, $2 is application

if [ -z "$1" ]
then
    echo "No driver specified"
    exit 1
fi

if [ -z "$2" ]
then
    echo "No application specified"
    exit 1
fi

rm -rf build
cp -r frame build
cp -r $1/* build
cp -r $2/* build

# extraneous file removal
cd build
find . -type d -name __pycache__ -exec rm -r {} \+
rm -f README.md
cd - 
