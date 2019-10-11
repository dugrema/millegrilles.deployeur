from setuptools import setup
import subprocess


def get_version():
    try:
        with open('version.txt', 'r') as version_file:
            version = version_file.readline().strip()
    except FileNotFoundError as e:
        with open('build.txt', "r") as buildno_file:
            build_no = buildno_file.read().strip()

        commande_git_version = ['git', 'name-rev', '--name-only', 'HEAD']
        output_process = subprocess.run(commande_git_version, stdout=subprocess.PIPE)
        version = output_process.stdout.decode('utf8').strip()
        version = '%s.%s' % (version, build_no)
        print("Version: %s" % (version))

    return version

setup(
    name='MilleGrilles.deployeur',
    version='%s' % get_version(),
    packages=['mgdeployeur'],
    url='',
    license='',
    author='Mathieu Dugre',
    author_email='',
    description=''
)
