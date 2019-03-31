Role Name
=========

A brief description of the role goes here.

Requirements
------------

* R 3.2+
* rpy2 on target machines
  * rpy2==2.8.6 if using Python 2
* R devtools (if installing specific versions of packages)

Example Playbook
----------------

```yml
---
- name: Test evandam.r_package
  hosts: all
  roles:
    - role: evandam.r_package
  tasks:
    - name: Install devtools
      r_package:
        name: devtools
        state: present

    - name: Install dplyr 0.8.0
      r_package:
        name: dplyr
        version: 0.8.0

    - name: Install a list of packages
      r_package:
        name:
          - dplyr=0.8.0
          - readr
          - tidyr
          - purrr

    - name: Remove a package
      r_package:
        name: readr
        state: absent

    - name: Make a library location for new packages
      file:
        path: /tmp/R
        state: directory

    - name: Install a package into a different library
      r_package:
        name: dplyr
        lib: /tmp/R
```

To Do:
------
* Support installing local packages. Ex:
```yml
- r_package:
    name: foo
    src: /tmp/foo.tar.gz
```

License
-------

BSD
