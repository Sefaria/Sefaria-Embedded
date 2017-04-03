package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"time"

	"encoding/gob"

	"strings"

	"github.com/boltdb/bolt"
	"gopkg.in/gin-gonic/gin.v1"
)

type SefariaAPIResult struct {
	HebrewText              []string `json:"he" binding:"required"`
	EnglishText             []string `json:"text" binding:"required"`
	HebrewSectionReference  string   `json:"heSectionRef" binding:"required"`
	EnglishSectionReference string   `json:"sectionRef" binding:"required"`
}

var db *bolt.DB

func init() {
	var err error
	db, err = initDB()
	if err != nil {
		log.Fatal(err)
	}
}

func main() {

	r := gin.Default()
	r.LoadHTMLGlob("./templates/*")

	r.GET("/e/:resource", getEmbed)

	r.Run(":3017")
}

func getEmbed(c *gin.Context) {
	idString := c.Param("resource")
	url := buildSefariaGetURL(idString)
	result, err := getData(url, db)

	if err != nil {
		c.String(http.StatusInternalServerError, err.Error())
		return
	}

	c.HTML(http.StatusOK, "embed.tmpl", gin.H{
		"defaultLanguageCode": "he",
		"textHebrew":          result.HebrewText,
		"textEnglish":         result.EnglishText,
		"secRefHebrew":        result.HebrewSectionReference,
		"secRefEnglish":       result.EnglishSectionReference,
		"originalURLPath":     idString,
	})
}

func initDB() (*bolt.DB, error) {
	db, err := bolt.Open(CONFIG_DBNAME, 0600, &bolt.Options{Timeout: 1 * time.Second})
	if err != nil {
		return nil, err
	}

	err = db.Update(func(tx *bolt.Tx) error {
		_, err := tx.CreateBucketIfNotExists([]byte(CONFIG_BUCKETNAME))

		if err != nil {
			return fmt.Errorf("Create bucket: %s", err)
		}
		return nil
	})

	err = db.Update(func(tx *bolt.Tx) error {
		_, err := tx.CreateBucketIfNotExists([]byte("integrated"))

		if err != nil {
			return fmt.Errorf("Create bucket: %s", err)
		}
		return nil
	})

	if err != nil {
		return nil, err
	}
	return db, nil
}

func buildSefariaGetURL(rawurl string) string {
	url, err := url.Parse(rawurl)
	if err != nil {
		panic(err)
	}
	fmt.Println(url)
	url.Host = "www.sefaria.org"
	url.Scheme = "http"
	url.Path = "api/texts/" + url.Path
	return url.String()
}

func sefariaGet(url string) (SefariaAPIResult, error) {
	var m SefariaAPIResult

	resp, err := http.Get(url)
	if err != nil {
		return m, err
	}

	decoder := json.NewDecoder(resp.Body)
	if err := decoder.Decode(&m); err != nil {
		return m, err
	}
	m.Sanitize()
	return m, nil
}

//Sanitize removes certain patterns known to be in the data
//that are problematic. Sanitize should be called when pulling
//in new data from the Sefaria API.
func (r SefariaAPIResult) Sanitize() {
	//First known case of sanitization is removing the <i></i>
	//tags from within the english text data
	for i := range r.EnglishText {
		r.EnglishText[i] = strings.Replace(r.EnglishText[i], "<i></i>", "", -1)
	}
}

func putData(key string, data SefariaAPIResult, db *bolt.DB) error {
	err := db.Update(func(tx *bolt.Tx) error {
		b := tx.Bucket([]byte("integrated"))
		buf := new(bytes.Buffer)
		enc := gob.NewEncoder(buf)
		err := enc.Encode(data)
		if err != nil {
			return err
		}
		err = b.Put([]byte(key), buf.Bytes())
		if err != nil {
			return err
		}
		return nil
	})
	return err
}

func getData(key string, db *bolt.DB) (SefariaAPIResult, error) {
	var data SefariaAPIResult
	doesExist := false
	//Check to see if it exists locally
	err := db.View(func(tx *bolt.Tx) error {
		b := tx.Bucket([]byte("integrated"))

		if result := b.Get([]byte(key)); result != nil {
			doesExist = true
			buf := bytes.NewBuffer(result)
			dec := gob.NewDecoder(buf)
			err := dec.Decode(&data)
			return err
		}
		return nil
	})

	//If it doesn't, go ask Sefaria for it
	if doesExist == false {
		data, err = sefariaGet(key)

		// And save it
		putData(key, data, db)
	}
	return data, err
}
