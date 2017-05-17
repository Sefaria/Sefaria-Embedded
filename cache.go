package main

import (
	"bytes"
	"encoding/gob"
	"time"

	"log"

	"github.com/boltdb/bolt"
)

func cacheManager() {
	d := time.Duration(CONFIG_CLEAN_DB_DURATION_SECONDS) * time.Second
	tickChannel := time.Tick(d)
	for _ = range tickChannel {
		cleanDB()
	}
}

func cleanDB() error {
	xKeys, err := getExpiredKeys()
	if err != nil {
		return err
	}

	err = purgeExpiredKeys(xKeys)
	if err != nil {
		return err
	}

	return nil
}

//getExpiredKeys uses a read-only transaction to create a list of keys that are expired
func getExpiredKeys() ([]string, error) {
	var expiredKeys []string
	var data SefariaResource

	err := db.View(func(tx *bolt.Tx) error {
		b := tx.Bucket([]byte("integrated"))

		c := b.Cursor()

		for k, v := c.First(); k != nil; k, v = c.Next() {

			buf := bytes.NewBuffer(v)
			dec := gob.NewDecoder(buf)
			err := dec.Decode(&data)
			if err != nil {
				return err
			}
			t := time.Since(data.LastTouched)
			if t > time.Second*CONFIG_CACHE_PURGE_SECONDS {
				expiredKeys = append(expiredKeys, string(k))
			}

		}

		return nil
	})

	if err != nil {
		return nil, err
	}
	return expiredKeys, nil
}

//purgeExpiredKeys uses a read-write transaction to delete a list of keys
func purgeExpiredKeys(xKeys []string) error {
	err := db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket([]byte("integrated"))

		for _, elem := range xKeys {
			log.Printf("Resource deleted: %s\n", elem)
			err := b.Delete([]byte(elem))
			if err != nil {
				return err
			}
		}

		return nil
	})

	if err != nil {
		return err
	}
	return nil
}
