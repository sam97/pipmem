# pipmem #
pipmem is simply memory for pip. By default the pip package manager for Python does not log what it does except for the terminal as it is run. This script is an attempt to solve for this.

### What pipmem is not ###
pipmem is not a replacement for pip, it actually requires it. But simply it sits on top of pip, the heavy lifting is still done via pip in the background. pipmem does not connect directly to PyPI to download packages, and any changes performed directly with pip are not logged.

It is also not a replacement for virtual environments nor does it plan to compete with it. They can be complementary however as pipmem will be able to operate on virtual environments including when they are inactive to track package changes.

### Usage ###
pipmem operates similar to pip in that you call it with an action then any required options.
<br />
The actions are meant to self explanatory but more detail can be seen by passing it the -h option. Below is an overview of the primary actions included.

    usage: pipmem.py [-h] {install,uninstall,history} ...
    
    pipmem is used to keep track of action performed by the pip package manager.
    
    positional arguments:
      {install,uninstall,history}
        install             Install packages.
        uninstall           Unnstall packages.
        history             Transaction history data
    
    optional arguments:
      -h, --help            show this help message and exit

### Contributing ###
Please provide any feedback including bugs, errors, requests, or suggestions via issues on this project's GitHub page.

Any pull requests should be made against the dev branch.