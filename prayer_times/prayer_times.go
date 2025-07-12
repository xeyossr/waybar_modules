package main

import (
	"github.com/tidwall/gjson"
	"github.com/joho/godotenv"
	"fmt"
	"io"
	"os"
	"time"
	"path/filepath"
	"net/http"
)

type Config struct {
	City string
	CountryCode string
	CalcMethod string
}

type PrayerTimes struct {
	Fajr string
	Dhuhr string
	Asr string
	Maghrib string
	Isha string
}

func checkError(err error) {
	if err != nil {
		panic(err)
	}
}

func getEnv(key, defaultvar string) string {
	val := os.Getenv(key)
	
	if val == "" {
		return defaultvar
	}
	
	return val
}

func loadEnvs(path string) (config Config, err error) {
	err = godotenv.Load(path)

	// Get Variables
	config.City = getEnv("CITY", "Istanbul")
	config.CountryCode = getEnv("COUNTRY_CODE", "Turkey")
	config.CalcMethod = getEnv("PRAYER_CALC_METHOD", "4")

	return config, err
}

func request(url string) (string) {
	resp, err := http.Get(url)
	checkError(err)
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	checkError(err)

	return string(body)
}

func afterIsha(layout, todayStr, isha string, config Config) (string) {
	now := time.Now()
	layout = fmt.Sprintf("%s 15:04", layout)
	tomorrow := now.Add(24 * time.Hour)
	tomorrowStr := tomorrow.Format(layout)

	targetStr := fmt.Sprintf("%s %s", todayStr, isha)
	targetTime, err := time.Parse(layout, targetStr)
	checkError(err)
	
	if now.After(targetTime) {
		url := fmt.Sprintf(
  		"https://api.aladhan.com/v1/timingsByAddress/%s?address=%s%%2C+%s&method=%s",
  		tomorrowStr, config.City, config.CountryCode, config.CalcMethod,
		)

		jsonStr := request(url)
		return jsonStr
	}
	
	return ""
}

func getPrayerTimes(config Config, layout string) (PrayerTimes) {
	now := time.Now()
	todayStr := now.Format(layout)
	
	url := fmt.Sprintf(
  	"https://api.aladhan.com/v1/timingsByAddress/%s?address=%s%%2C+%s&method=%s",
  	todayStr, config.City, config.CountryCode, config.CalcMethod,
	)
	
	jsonStr := request(url)
	isha := gjson.Get(jsonStr, "data.timings.Isha")
	
	AfterIsha := afterIsha(layout, todayStr, isha.String(), config)
	
	if AfterIsha != "" {
		jsonStr = AfterIsha
	}

	var prayertimes PrayerTimes
	prayertimes.Fajr = gjson.Get(jsonStr, "data.timings.Fajr").String()
	prayertimes.Dhuhr = gjson.Get(jsonStr, "data.timings.Dhuhr").String()
	prayertimes.Asr = gjson.Get(jsonStr, "data.timings.Asr").String()
	prayertimes.Maghrib = gjson.Get(jsonStr, "data.timings.Maghrib").String()
	prayertimes.Isha = gjson.Get(jsonStr, "data.timings.Isha").String()

	return prayertimes
}

func formatTooltip(prayers PrayerTimes) string {
	tooltip := fmt.Sprintf("Fajr: %s\\nDhuhr: %s\\nAsr: %s\\nMaghrib: %s\\nIsha: %s", prayers.Fajr, prayers.Dhuhr, prayers.Asr, prayers.Maghrib, prayers.Isha)
	return tooltip
}

func main() {
	homeDir, err := os.UserHomeDir()
	checkError(err)

	stateRC := filepath.Join(homeDir, ".local", "state", ".staterc")
	config, err := loadEnvs(stateRC)
	checkError(err)
	
	layout := "02-01-2006"
	//timelayout := fmt.Sprintf("%s 15:04", layout)
	p := getPrayerTimes(config, layout)
	
	/*
	times := map[string]string{
		"Fajr":    p.Fajr,
		"Dhuhr":   p.Dhuhr,
		"Asr":     p.Asr,
		"Maghrib": p.Maghrib,
		"Isha":    p.Isha,
	}*/
	
	//now := time.Now()
	//todayStr := now.Format(layout)
	//currentTimeStr := now.Format("15:04")
	//currentFullTime := fmt.Sprintf("%s %s", todayStr, currentTimeStr)
	//parsedNow, err := time.Parse("02-01-2006 15:04", currentFullTime)
	//checkError(err)
	
	/*
	var next_prayer string
	//var prayer_diff string

	for name, timeStr := range times {
		fullTime := fmt.Sprintf("%s %s", todayStr, timeStr)
		t, err := time.Parse(timelayout, fullTime)
		checkError(err)

		if t.After(parsedNow) {
			next_prayer = name
			break
		}
	}
	*/

	tooltip := formatTooltip(p)
	output := fmt.Sprintf("{\"text\": \"\", \"tooltip:\": \"%s\"}", tooltip)
	fmt.Println(output)
}

