# Notes

## Hashing (general)
* Secure hash function?
* **SHA2** currently the standard.
	* If found vulnerable in the future --> SHA3 is already available and seen as secure

* **Idé:** Generera hash --> generera salt --> hasha --> skicka 

## Secure password hashing 
* No: 
	* MD5
	* SHA-1 
	* SHA-256
* Yes:
	* Scrypt -- **USE THIS** 
	* Bcrypt
		* Has been cracked? 
	* Argon2 -- **OR THIS**
		* Won password hashing competition (PHC) in 2015

1. Generate unique and sufficiently long password 
2. Generate salt 
	* Publicly known
	* Random value
3. Prepend salt to password 
4. Hash password + salt 
5. Store user name, salt and password hash together